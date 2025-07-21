"""orca_chat/core/graph.py"""

import asyncio
from collections.abc import Callable, Mapping, Sequence

from langgraph.graph import END
from langgraph.graph.state import CompiledStateGraph, StateGraph

from .registry import LLMRegistry, NodeFactory
from .session import LLMSession

SkillName = str
Predicate = Callable[[LLMSession], bool]
ConditionalEdge = tuple[SkillName, SkillName, Predicate]
RoutingTable = dict[SkillName, list[tuple[SkillName, Predicate]]]


async def build_graph(
    registry: LLMRegistry,
    pipeline: Sequence[SkillName],
    *,
    conditionals: Sequence[ConditionalEdge] | None = None,
) -> CompiledStateGraph:
    """Compile a state graph from a skill pipeline.

    Parameters
    ----------
    registry
        Registry providing node factories.
    pipeline
        Ordered skill names.
    conditionals
        ``(src, dst, predicate)`` routes evaluated after each node.
    """

    if not pipeline:
        raise ValueError("Pipeline must contain at least one node")

    factories = await _load_factories(registry, pipeline)
    sg: StateGraph[LLMSession] = StateGraph(LLMSession)

    _add_linear_edges(
        sg,
        pipeline,
        factories,
        skip_sources={src for src, *_ in conditionals or ()},
    )
    if conditionals:
        _add_conditional_edges(sg, pipeline, conditionals)

    sg.set_entry_point(pipeline[0])
    sg.set_finish_point(pipeline[-1])

    return sg.compile()


async def _load_factories(
    registry: LLMRegistry, pipeline: Sequence[SkillName]
) -> Mapping[SkillName, NodeFactory]:
    tasks = [registry.get_factory(node) for node in pipeline]
    results = await asyncio.gather(*tasks)
    return dict(zip(pipeline, results, strict=False))


def _add_linear_edges(
    sg: StateGraph[LLMSession],
    pipeline: Sequence[SkillName],
    factories: Mapping[SkillName, NodeFactory],
    *,
    skip_sources: set[SkillName] | None = None,
) -> None:
    skip_sources = skip_sources or set()
    for i, name in enumerate(pipeline):
        sg.add_node(name, factories[name]())
        if i > 0 and pipeline[i - 1] not in skip_sources:
            sg.add_edge(pipeline[i - 1], name)


def _add_conditional_edges(
    sg: StateGraph[LLMSession],
    pipeline: Sequence[SkillName],
    conditionals: Sequence[ConditionalEdge],
) -> None:
    routing_table = _group_conditionals(pipeline, conditionals)

    for src, cases in routing_table.items():
        default_dst = END

        def _router(state: LLMSession, *, _cases=cases, _default=default_dst, _src=src):
            for dst, pred in _cases:
                if pred(state):
                    return dst
            if _default is None:
                raise ValueError(f"No branch matched for node {_src}")
            return _default

        sg.add_conditional_edges(src, _router)


def _group_conditionals(
    pipeline: Sequence[SkillName], conditionals: Sequence[ConditionalEdge]
) -> RoutingTable:
    routing_table: RoutingTable = {}
    for src, dst, pred in conditionals:
        if src not in pipeline or dst not in pipeline:
            raise ValueError(f"Conditional {src}->{dst} references unknown node(s).")
        routing_table.setdefault(src, []).append((dst, pred))
    return routing_table

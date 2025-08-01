"""orca_chat/core/graph.py"""

from collections.abc import Callable, Sequence
from functools import partial
from typing import Final

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .llm import LLMStore
from .node import NodeStore
from .session import Session

__all__: Final = ["build_graph"]


Predicate = Callable[[], bool]
"""A predicate evaluated against *Session* **state**.

The predicate receives the **current** :class:`Session` and must return
``True`` if the edge should be taken, ``False`` otherwise.
"""

ConditionalEdge = tuple[str, str, Predicate]
"""A conditional edge of the form ``(src, dst, predicate)``.

* **src**: Node where the routing decision is made.
* **dst**: Node entered when *predicate* is satisfied.
* **predicate**: A :pydata:`Predicate`, evaluates ``True`` or ``False``.
"""

RoutingTable = dict[str, list[tuple[str, Predicate]]]
"""Mapping of ``src`` to list of ``(dst, predicate)`` pairs."""


async def build_graph(
    pipeline: Sequence[str],
    conditionals: Sequence[ConditionalEdge] | None = None,
    *,
    llm_store: LLMStore,
    node_store: NodeStore,
    default_llm_alias="default",
) -> CompiledStateGraph:
    """Wire *pipeline* nodes into a :class:`CompiledStateGraph`.

    The function constructs a *LangGraph* state machine from a linear list of
    *pipeline* node names. Every node is looked-up in *node_store* and, if it
    requires an LLM, is partially applied with the *default* model retrieved
    from *llm_store*.

    Parameters
    ----------
    pipeline
        Names of the nodes **in execution order**. The first element becomes
        the *entry point*, the last the *finish point*.
    conditionals
        Optional list of *conditional edges* expressed as triples
        ``(src, dst, predicate)``. During runtime the *predicate* is evaluated
        **sequentially**; the first ``dst`` whose predicate returns ``True`` is
        taken. When none match, the graph falls through to :pydata:`END`.
    llm_store
        Registry of named chat models, consulted whenever a node factory is
        tagged with ``"llm"``.
    node_store
        Registry of node *factories*. Factories must accept an optional LLM
        instance as their first argument when they are tagged accordingly.
    default_llm_alias
        Alias to look-up in *llm_store* whenever an LLM-aware factory is wired
        and a specific LLM alias is not provided internally.

    Returns
    -------
    CompiledStateGraph
        A compiled, ready-to-run state graph.

    Raises
    ------
    ValueError
        * If *pipeline* is empty.
        * If *conditionals* reference unknown *src* or *dst* nodes.

    Examples
    --------
    >>> graph = await build_graph(
    ...     pipeline=["load", "parse", "respond"],
    ...     conditionals=[
    ...         ("parse", "respond", lambda s: s.ok),
    ...     ],
    ...     llm_store=my_llm_store,
    ...     node_store=my_node_store,
    ... )
    >>> result = await graph.arun(Session())
    """

    if not pipeline:
        raise ValueError("Cannot build graph with empty pipeline")

    graph = StateGraph(Session)

    # - - - - - - - - - - - - - - - -
    # 1. Add linear edges
    # - - - - - - - - - - - - - - - -

    for i, name in enumerate(pipeline):
        factory = await node_store.get_factory(name)

        # Some factories expect an LLM as their first positional argument. We
        # detect those via the "llm" tag and freeze the model into the partial
        # so the graph can call it without knowing about LLMs.
        if "llm" in getattr(factory, "tags", ()):
            llm = llm_store.get(default_llm_alias)
            runnable = partial(factory, llm)
        else:
            runnable = factory
        graph.add_node(name, runnable)

        # Connect the previous node to *name* **unless** that previous node is
        # the *source* of a conditional edge. Conditional sources need to
        # decide at runtime where to go, so we leave them dangling for now.
        skip_starts = {src for src, *_ in conditionals or ()}
        if i > 0 and pipeline[i - 1] not in skip_starts:
            graph.add_edge(pipeline[i - 1], name)

    # - - - - - - - - - - - - - - - -
    # 2. Add conditional edges
    # - - - - - - - - - - - - - - - -

    if conditionals:
        routing_table: RoutingTable = {}

        # Group edges by *src* to simplify router creation.
        for src, dst, predicate in conditionals:
            if src not in pipeline or dst not in pipeline:
                raise ValueError(f"Unknown conditional: {src!r}->{dst!r}")
            routing_table.setdefault(src, []).append((dst, predicate))

        # Build a dedicated router closure for each *src*.
        for src, cases in routing_table.items():

            def _router(state: Session, _cases=cases):
                """Return the first *dst* where predicate matches *state*.

                If no predicate returns ``True`` we fall through to
                :pydata:`END`, signalling no further work.
                """
                for dst, predicate in _cases:
                    if predicate(state):
                        return dst
                return END

            # Wire up our dangling edges.
            graph.add_conditional_edges(src, _router)

    # - - - - - - - - - - - - - - - -
    # 3. Finalize; return
    # - - - - - - - - - - - - - - - -

    graph.set_entry_point(pipeline[0])
    graph.set_finish_point(pipeline[-1])
    return graph.compile()

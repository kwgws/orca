# orca_chat/core/graph.py

from collections.abc import Sequence
from typing import Final, Protocol

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .node import Node
from .session import Session

__all__: Final = ["build_graph"]


class Predicate(Protocol):
    """A predicate evaluated against the session state.

    The predicate receives the current :class:`Session` and returns ``True``
    if the edge should be taken, ``False`` otherwise.
    """

    def __call__(self, state: Session) -> bool: ...


NodeName = str

ConditionalEdge = tuple[Node[Session], Node[Session], Predicate]
"""A conditional edge of the form ``(src, dst, predicate)``.

- ``src``: Node where the routing decision is made.
- ``dst``: Node entered when *predicate* is satisfied.
- ``predicate``: A :class:`Predicate`, evaluates ``True`` or ``False``.
"""

RoutingTable = dict[NodeName, list[tuple[NodeName, Predicate]]]
"""Mapping of ``src`` to list of ``(dst, predicate)`` pairs."""


async def build_graph(
    pipeline: Sequence[Node[Session]],
    conditionals: Sequence[ConditionalEdge] | None = None,
) -> CompiledStateGraph[Session]:
    """Construct and compile a LangGraph ``StateGraph``.

    The graph executes ``pipeline`` left-to-right. For any node listed as a
    conditional source, control is delegated to a router that evaluates
    predicates in the order provided and jumps to the first matching
    destination. When no predicate matches, the graph terminates.

    Notes
    -----
    - ``pipeline`` must contain at least one node and every node referenced
      in ``conditionals`` must appear in pipeline.
    - Predicates MUST be side-effect-free; they're evaluated during routing,
      potentially multiple times.

    Parameters
    ----------
    pipeline
        Sequence of nodes in execution order. The first element becomes the
        entry point, the last the finish point.
    conditionals
        Optional list of conditional edges expressed as triples, e.g.
        ``(src, dst, predicate)``. During runtime these are evaluated
        sequentially; the first ``dst`` whose predicate returns ``True`` is
        taken. When none match, the graph falls through to :pydata:`END`.

    Returns
    -------
    CompiledStateGraph
        A compiled, ready-to-run state graph.

    Raises
    ------
    ValueError
        - If ``pipeline`` is empty.
        - If ``conditionals`` references unknown nodes.
        - If multiple nodes in ``pipeline`` share the same ``node.name``.

    Examples
    --------
    >>> session = Session()
    ... graph = await build_graph(
    ...     pipeline=[load_node, parse_node, parse_node],
    ...     conditionals=[
    ...         (parse_node, parse_node, lambda s: s.ok),
    ...     ],
    ... )
    >>> result = await graph.arun(session)
    """

    if not pipeline:
        raise ValueError("Cannot build graph with empty pipeline")

    graph = StateGraph(Session)

    # - - - - - - - - - - - - - - - -
    # 1. Add linear edges
    # - - - - - - - - - - - - - - - -

    # Conditional sources need to decide at runtime where to go, so we leave
    # them dangling for now.
    ignored = {src.name for src, *_ in conditionals or ()}

    for i, node in enumerate(pipeline):
        if node.name in graph.nodes:
            raise ValueError(f"Duplicate node name in pipeline: {node.name!r}")

        graph.add_node(node.name, node.factory)

        # Connect this node to its predecessor unless that that node is the
        # source of a conditional edge.
        if i > 0 and pipeline[i - 1].name not in ignored:
            graph.add_edge(pipeline[i - 1].name, node.name)

    # - - - - - - - - - - - - - - - -
    # 2. Add conditional edges
    # - - - - - - - - - - - - - - - -

    if conditionals:
        routing_table: RoutingTable = {}

        # Group edges by src to simplify router creation. The router logic
        # requires hashable identifiers, so we temporarily fall back to using
        # the name of each node rather than the objects themselves.
        for src, dst, pred in ((s.name, d.name, p) for s, d, p in conditionals):
            if src not in graph.nodes or dst not in graph.nodes:
                raise ValueError(f"Unknown conditional edge: {src!r}->{dst!r}")

            routing_table.setdefault(src, []).append((dst, pred))

        # Build a dedicated router closure for each src.
        for src, cases in routing_table.items():

            def _router(state: Session, _cases=cases):
                """Return the first *dst* where predicate matches *state*.

                If no predicate returns ``True`` we fall through to
                :pydata:`END`, signalling no further work.
                """
                for dst, pred in _cases:
                    if pred(state):
                        return dst
                return END

            # Go back and wire up our dangling edges to their respective
            # router closures.
            graph.add_conditional_edges(src, _router)

    # - - - - - - - - - - - - - - - -
    # 3. Finalize; return
    # - - - - - - - - - - - - - - - -

    graph.set_entry_point(pipeline[0].name)
    graph.set_finish_point(pipeline[-1].name)
    return graph.compile()

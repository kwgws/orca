"""orca_chat/core/graph.py"""

from collections.abc import Sequence
from typing import Final, Protocol

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .node import Node, NodeStore
from .session import Session

__all__: Final = ["build_graph"]


class Predicate(Protocol):
    """A predicate evaluated against *Session* **state**.

    The predicate receives the **current** :class:`Session` and must return
    ``True`` if the edge should be taken, ``False`` otherwise.
    """

    def __call__(self, state: Session) -> bool: ...


ConditionalEdge = tuple[Node, Node, Predicate]
"""A conditional edge of the form ``(src, dst, predicate)``.

* **src**: Node where the routing decision is made.
* **dst**: Node entered when *predicate* is satisfied.
* **predicate**: A :pydata:`Predicate`, evaluates ``True`` or ``False``.
"""

RoutingTable = dict[Node, list[tuple[Node, Predicate]]]
"""Mapping of ``src`` to list of ``(dst, predicate)`` pairs."""


async def build_graph(
    pipeline: Sequence[Node],
    conditionals: Sequence[ConditionalEdge] | None = None,
    *,
    node_store: NodeStore,
) -> CompiledStateGraph:
    """Wire *pipeline* nodes into a :class:`CompiledStateGraph`.

    Parameters
    ----------
    pipeline
        Sequence of nodes **in execution order**. The first element becomes
        the *entry point*, the last the *finish point*.
    conditionals
        Optional list of *conditional edges* expressed as triples
        ``(src, dst, predicate)``. During runtime the *predicate* is evaluated
        **sequentially**; the first ``dst`` whose predicate returns ``True`` is
        taken. When none match, the graph falls through to :pydata:`END`.
    node_store
        Registry of node *factories*. Factories must accept an optional LLM
        instance as their first argument when they are tagged accordingly.

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
    ...     pipeline=[load_node, parse_node, parse_node],
    ...     conditionals=[
    ...         (parse_node, parse_node, lambda s: s.ok),
    ...     ],
    ...     node_store=my_node_store,
    ... )
    >>> result = await graph.arun(Session())
    """

    if not pipeline:
        raise ValueError("Cannot build graph with empty pipeline")

    graph = StateGraph(Session)
    conditional_srcs = {src for src, *_ in conditionals or ()}

    # - - - - - - - - - - - - - - - -
    # 1. Add linear edges
    # - - - - - - - - - - - - - - - -

    for i, node in enumerate(pipeline):
        node = await node_store.get(node.name)

        # Add a default RunnableConfig, just in case.
        graph.add_node(node.name, node.factory)

        # Connect the previous node to *name* **unless** that previous node is
        # the *source* of a conditional edge. Conditional sources need to
        # decide at runtime where to go, so we leave them dangling for now.
        if i > 0 and pipeline[i - 1] not in conditional_srcs:
            graph.add_edge(pipeline[i - 1].name, node.name)

    # - - - - - - - - - - - - - - - -
    # 2. Add conditional edges
    # - - - - - - - - - - - - - - - -

    if conditionals:
        routing_table: RoutingTable = {}

        # Group edges by *src* to simplify router creation.
        for src, dst, predicate in conditionals:
            if src not in pipeline or dst not in pipeline:
                raise ValueError(f"Unknown conditional: {src.name!r}->{dst.name!r}")
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
            graph.add_conditional_edges(src.name, _router)

    # - - - - - - - - - - - - - - - -
    # 3. Finalize; return
    # - - - - - - - - - - - - - - - -

    graph.set_entry_point(pipeline[0].name)
    graph.set_finish_point(pipeline[-1].name)
    return graph.compile()

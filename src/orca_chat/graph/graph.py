# --- orca_chat/graph/graph.py ------------------------------------------------

"""Conversation graph implementation for Orca Chat.

Defines the LangGraph execution plan that manages the conversational backend
for Orca Chat.
"""

from collections.abc import Sequence
from typing import Any, Final, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, START
from langgraph.graph.state import StateGraph

from .nodes import pilot_node, prune_node, reply_node, tools_node
from .state import State, get_last_msg

__all__: Final = [
    "make_graph",
]

PILOT: Final = "pilot"
TOOLS: Final = "tools"
REPLY: Final = "reply"
PRUNE: Final = "prune"
ROUTE_TO_REPLY: Final = "route_to_reply"


# --- Defaults ----------------------------------------------------------------


MAX_TOOL_LOOPS: Final = 2
MAX_HUMAN_MSGS: Final = 6
MIN_HUMAN_MSGS: Final = 2


# --- Edges -------------------------------------------------------------------


def _pilot_wants_tools(msg: AIMessage) -> bool:
    """..."""

    def _get_tool_name(tc: Any) -> str:
        """..."""

        if hasattr(tc, "name"):
            return tc.name
        if isinstance(tc, dict):
            return (
                tc.get("name")
                or tc.get("function", {}).get("name")
                or tc.get("tool", {}).get("name")
            )
        return ""

    tool_calls = msg.tool_calls or msg.additional_kwargs.get("tool_calls") or []
    return any(
        (name := _get_tool_name(tc)) and name != ROUTE_TO_REPLY
        for tc in tool_calls
    )


@tool(ROUTE_TO_REPLY)
def _route_to_reply() -> str:
    """Route message directly to chat; no tool execution necessary."""
    return ROUTE_TO_REPLY


def _to_tools():
    """Decide whether or not to send the message for tool execution."""

    def _route(state: State) -> str:
        if isinstance(msg := get_last_msg(state), AIMessage):
            if _pilot_wants_tools(msg):
                return TOOLS
        return REPLY

    return _route


def _to_reply(*, max_tool_loops: int):
    """Decide whether to send back to PILOT or on to REPLY."""

    def _count_tool_rounds(state: State) -> int:
        rounds = 0
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                break
            elif isinstance(msg, AIMessage):
                if _pilot_wants_tools(msg):
                    rounds += 1
        return rounds

    def _route(state: State) -> str:
        if _count_tool_rounds(state) >= max_tool_loops:
            return REPLY
        return PILOT

    return _route


def _to_prune(*, max_human_msgs: int):
    """Decide whether or not to summarize and prune."""

    def _count_human_msgs(state: State) -> int:
        return sum(isinstance(msg, HumanMessage) for msg in state["messages"])

    def _route(state: State) -> str:
        if _count_human_msgs(state) >= max_human_msgs:
            return PRUNE
        return END

    return _route


# --- Graph -------------------------------------------------------------------


def make_graph(
    *,
    llm: BaseChatModel,
    tools: Sequence[BaseTool],
    max_tool_loops: int = MAX_TOOL_LOOPS,
    min_human_msgs: int = MIN_HUMAN_MSGS,
    max_human_msgs: int = MAX_HUMAN_MSGS,
    **_,
) -> StateGraph[State]:
    """..."""

    prune_llm = llm
    tools_llm = cast(BaseChatModel, llm.bind_tools([*tools, _route_to_reply]))

    graph = StateGraph(State)

    # Nodes
    graph.add_node(PILOT, pilot_node(tools_llm))
    graph.add_node(TOOLS, tools_node(tools))
    graph.add_node(REPLY, reply_node(llm))
    graph.add_node(PRUNE, prune_node(prune_llm, min_human_msgs=min_human_msgs))

    # Edges
    graph.add_edge(START, PILOT)
    graph.add_conditional_edges(PILOT, _to_tools())
    graph.add_conditional_edges(TOOLS, _to_reply(max_tool_loops=max_tool_loops))
    graph.add_conditional_edges(REPLY, _to_prune(max_human_msgs=max_human_msgs))
    graph.add_edge(PRUNE, END)

    return graph

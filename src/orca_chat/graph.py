# orca_chat/graph.py

"""Conversation graph implementation for Orca Chat.

Defines the LangGraph execution plan that manages the conversational backend
for Orca Chat.

Nodes
-----
Router
    Lightweight LLM decision node determining if a tool invocation is needed.
ChatTools
    Enhanced chat node responsible for generating initial responses and
    determining tool invocation from chat interactions.
Tools
    Executes tools as requested by the chat node, returning results.
Chat
    Full-featured chat node turning tool results or standard queries into
    er-friendly replies.
Summarize
    Manages message summarization to maintain efficient transcript size.

Flowchart
---------
```mermaid
flowchart TD
    %% Nodes
    RouterNode[ROUTER]
    ChatToolsNode[CHAT_TOOLS]
    ToolNode[ToolNode]
    ChatNode[CHAT]
    SummarizeNode[SUMMARIZE]

    %% Edges
    NeedsTools?{_needs_tools}
    ToolsCalled?{_calls_tools}
    NeedsSummary?{_needs_summary}

    %% Graph
    START((START)) --> RouterNode --> NeedsTools?
    NeedsTools? -->|tools| ChatToolsNode --> ToolsCalled?
    NeedsTools? -->|chat| ChatNode
    ToolsCalled? -->|tool_calls| ToolNode --> ChatNode
    ToolsCalled? -->ChatNode
    ChatNode --> NeedsSummary?
    NeedsSummary? -->|should_summarize| SummarizeNode --> END
    NeedsSummary? --> END(((END)))
```
"""

from collections.abc import Sequence
from typing import Final

from langchain_core.tools import BaseTool
from langgraph.graph.state import END, START, CompiledStateGraph, StateGraph
from langgraph.prebuilt import ToolNode

from .skills import chat_node, route_node, summarize_node
from .state import MAX_HUMAN_MESSAGES, ConversationState, should_summarize

__all__ = ["build_graph"]

ROUTER: Final = "router"
CHAT_TOOLS: Final = "chat_tools"
TOOLS: Final = "tools"
CHAT: Final = "chat"
SUMMARIZE: Final = "summarize"


def build_graph(
    *, tools: Sequence[BaseTool] | None = None
) -> CompiledStateGraph[ConversationState]:
    """Construct and compile the conversation execution graph.

    Parameters
    ----------
    tools
        Tools available for invocation. If ``None``, a simplified chat and
        summarize flow is used without tool execution.

    Returns
    -------
    CompiledStateGraph[ConversationState]
        A ready-to-run conversation state graph.
    """
    graph = StateGraph(ConversationState)

    if tools:
        graph.add_node(ROUTER, route_node())
        graph.add_node(CHAT_TOOLS, chat_node(tools=tools))
        graph.add_node(TOOLS, ToolNode(tools=tools))
        graph.add_node(CHAT, chat_node())
        graph.add_node(SUMMARIZE, summarize_node())

        graph.add_edge(START, ROUTER)
        graph.add_conditional_edges(ROUTER, _needs_tools)  # CHAT_TOOLS or CHAT
        graph.add_conditional_edges(CHAT_TOOLS, _calls_tools)  # TOOLS or CHAT
        graph.add_edge(TOOLS, CHAT)
        graph.add_conditional_edges(CHAT, _needs_summary)  # SUMMARIZE or END
        graph.add_edge(SUMMARIZE, END)

    else:
        graph.add_node(CHAT, chat_node())
        graph.add_node(SUMMARIZE, summarize_node())

        graph.add_edge(START, CHAT)
        graph.add_conditional_edges(CHAT, _needs_summary)  # SUMMARIZE or END
        graph.add_edge(SUMMARIZE, END)

    return graph.compile()


def _needs_tools(state: ConversationState) -> str:
    """Determine if the current conversation state requires tool invocation."""
    route = state["payload"].get("route", "chat")
    return CHAT_TOOLS if route.strip().lower() == "tools" else CHAT


def _calls_tools(state: ConversationState) -> str:
    """Determine if tool invocation has been requested in the latest message."""
    last = state["messages"][-1]
    return TOOLS if getattr(last, "tool_calls", None) else CHAT


def _needs_summary(state: ConversationState) -> str:
    """Check whether message summarization is needed."""
    return SUMMARIZE if should_summarize(state, MAX_HUMAN_MESSAGES) else END

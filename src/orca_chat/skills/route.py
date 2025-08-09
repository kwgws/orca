# orca_chat/skills/route.py

from typing import Any, Final

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import StateNode

from ..llm import get_llm
from ..state import ConversationState, get_history
from ..tools.routes import (
    route_to_archive_retriever,
    route_to_chat,
    route_to_secondary_source_retriever,
    route_to_wikipedia,
)

__all__: Final = [
    "route_node",
]


_INSTRUCTIONS = """
You are a router node for a Warren Court archival research tool. Your task is
to decide which channel(s) is/are needed for the user's most recent message.

You MUST call AT LEAST ONE of these tools:
- route_to_archive_retriever
- route_to_secondary_source_retriever
- route_to_wikipedia
- route_to_chat

Rules
-----
1) If one or more retrievers is/are clearly needed, call them. You may call
   multiple retrievers if each is individually justified.
2) If no retriever criteria are clearly met (> 90% confidence), route **ONLY**
   to the chat node. If you are uncertain, prefer this route.
3) Do **NOT** respond to the conversation or interact in any other way.
"""

_REMINDER = f"""
\n{'-' * 20}\n
Decide which routing tools are needed for this message and call them. You may
call multiple retrievers. If no retriever criteria are clearly met, route
**ONLY** to the chat node. If you are uncertain, prefer this route.

Do **NOT** respond to the conversation or interact in any other way.
"""

_TOOLS = [
    route_to_archive_retriever,
    route_to_secondary_source_retriever,
    route_to_wikipedia,
    route_to_chat,
]


def route_node(**llm_kwargs: Any) -> StateNode:
    """Router that selects retriever nodes or falls back to the chat node.

    The router binds four selection tools: the archive retriever, the secondary
    source retriever, the wikipedia retriever, and the chat. The model should
    call any/some/all of the retrievers OR fall back to the chat node.
    """

    async def _route(
        state: ConversationState, config: RunnableConfig, **_
    ) -> dict[str, Any]:
        patch = {"payload": {"retrievers": [], "route": "chat"}}

        history = get_history(state, include_summary=False)
        if not history:
            return patch

        if len(history) == 1:
            prompt = [
                SystemMessage(_INSTRUCTIONS),
                HumanMessage(str(history[0].content) + _REMINDER),
            ]
        else:  # len(history) > 1
            last = history.pop()
            prompt = [
                SystemMessage(_INSTRUCTIONS),
                *history,
                HumanMessage(str(last.content) + _REMINDER),
            ]

        llm = await get_llm(tools=_TOOLS, **llm_kwargs)
        reply = await llm.ainvoke(prompt, config=config)

        # Collect route calls
        routes: list[str] = []
        for tc in getattr(reply, "tool_calls", []) or []:
            route = (tc.get("name") or "").strip()
            if route == "route_to_chat":
                return patch  # Mutually exclusive--break here.
            elif route in {
                "route_to_archive_retriever",
                "route_to_secondary_source_retriever",
                "route_to_wikipedia",
            }:
                routes.append(route)
        if not routes:
            return patch  # Something went wrong here--push through to chat.

        seen = set()  # De-dupe.
        routes = [r for r in routes if not (r in seen or seen.add(r))]

        patch["payload"] = {
            # Happily, alphabetical order is also order of priority. Neat!
            "retrievers": sorted(routes),
            "route": "tools",
        }
        return patch

    return _route

# tests/_helpers.py

from typing import Any, Final
from uuid import uuid4

from langchain_core.runnables import RunnableConfig

from orca_chat.state import ConversationState

__all__: Final = [
    "run_node",
    "tc",
]


def tc(
    name: str, args: dict[str, Any] | None = None, tool_id: str | None = None
) -> dict[str, Any]:
    """Build a valid ``tool_call`` dictionary for :class:`AIMessage`"""
    return {
        "id": tool_id or f"call_{uuid4().hex[:8]}",
        "type": "tool_call",
        "name": name,
        "args": args or {},
    }


async def run_node(
    node: Any, state: ConversationState, config: RunnableConfig | None = None
) -> ConversationState:
    """Invoke a LangGraph node."""
    if hasattr(node, "ainvoke"):  # runnable
        return await node.ainvoke(state, config=config)
    return await node(state, config=config or {})  # async fn (state, config)

# orca_chat/skills/chat.py

from textwrap import dedent
from typing import Any, Final, cast

from langchain_core.messages import (
    AIMessage,
    SystemMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import StateNode

from ..llm import get_llm
from ..state import ConversationState, get_history

__all__: Final = ["chat_node"]


def chat_node(**llm_kwargs) -> StateNode:
    prompt = dedent("""
    You are Orca, a helpful AI assistant.
    """)

    async def _chat(
        state: ConversationState, config: RunnableConfig, **_
    ) -> dict[str, Any]:
        """..."""
        llm = await get_llm(**llm_kwargs)

        messages = [
            SystemMessage(prompt),
            *get_history(state),
        ]

        reply = await llm.ainvoke(messages, config=config)
        return {"messages": [cast(AIMessage, reply)]}

    return _chat

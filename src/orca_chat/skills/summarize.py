# orca_chat/skills/summarize.py

from textwrap import dedent
from typing import Any, Final

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import StateNode

from ..llm import get_llm
from ..state import ConversationState, get_history

__all__: Final = ["summarize_node"]


def summarize_node(**llm_kwargs) -> StateNode:
    prompt = dedent("""
    Summarize our conversation so far in a single, concise paragraph.
    """)

    async def _summarize(
        state: ConversationState, config: RunnableConfig, **_
    ) -> dict[str, Any]:
        llm = await get_llm(**llm_kwargs)

        messages = [
            *get_history(state),
            HumanMessage(prompt),
        ]

        reply = await llm.ainvoke(messages, config=config)
        return {"payload": {"summary": str(reply.content)}}

    return _summarize

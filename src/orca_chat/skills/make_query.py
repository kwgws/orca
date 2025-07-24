"""orca_chat/skills/make_query.py"""

from logging import getLogger
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ..core.session import ChatSession
from ..loaders import LLMConfig

log = getLogger(__name__)


def build(cfg: LLMConfig, *, llm: ChatOllama, **kwargs) -> StateNode:
    async def _make_query(state: ChatSession, config: RunnableConfig) -> dict[str, Any]:
        log.info("Entering node 'make_query'")

        prompt = cfg.prompt.format_messages(
            chat_history=state.get_abridged_history(),
            input=state.get_last_message(),
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt, config=config):
            tokens.append(str(chunk.content) or "")

        search_query = "".join(tokens)
        log.info("Wrote query: %s", search_query)

        return {"payload": {**state.payload, "search_query": search_query}}

    return _make_query

"""orca_chat/skills/disambiguate.py"""

from logging import getLogger
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ..core.session import ChatSession
from ..loaders import LLMConfig

log = getLogger(__name__)


def build(cfg: LLMConfig, *, llm: ChatOllama, **kwargs) -> StateNode:
    async def _disambiguate(state: ChatSession, config: RunnableConfig) -> dict[str, Any]:
        log.info("Entering node 'disambiguate'")
        node_config: RunnableConfig = {
            **config,
            "tags": [*(config.get("tags", [])), "node_disambiguate"],
        }

        prompt = cfg.prompt.format_messages(
            chat_history=state.get_abridged_history(),
            input=state.get_last_message(use_disambiguation=False),
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt, config=node_config):
            tokens.append(str(chunk.content) or "")

        disambiguation = "".join(tokens)
        return {"payload": {**state.payload, "disambiguation": disambiguation}}

    return _disambiguate

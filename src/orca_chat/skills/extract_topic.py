"""orca_chat/skills/extract_topic.py"""

import re
from logging import getLogger
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ..core.session import ChatSession
from ..loaders import LLMConfig

log = getLogger(__name__)
_re_whitespace = re.compile(r"\s+")


def build(cfg: LLMConfig, *, llm: ChatOllama, **kwargs) -> StateNode:
    async def _make_query(state: ChatSession, config: RunnableConfig) -> dict[str, Any]:
        log.info("Entering node 'extract_topic'")
        node_config: RunnableConfig = {
            **config,
            "tags": [*(config.get("tags", [])), "node_extract_topic"],
        }

        prompt = cfg.prompt.format_messages(
            chat_history=state.get_abridged_history(),
            input=state.get_last_message(),
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt, config=node_config):
            tokens.append(str(chunk.content) or "")
        topic = "".join(tokens)

        log.info("Extracted topic: %s", topic)
        return {"payload": {**state.payload, "topic": topic}}

    return _make_query

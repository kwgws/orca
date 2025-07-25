"""orca_chat/skills/route.py"""

from logging import getLogger
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ..core.session import ChatSession
from ..loaders import LLMConfig

log = getLogger(__name__)


def build(cfg: LLMConfig, *, llm: ChatOllama, **kwargs) -> StateNode:
    async def _route(state: ChatSession, config: RunnableConfig) -> dict[str, Any]:
        log.info("Entering node 'route'")
        node_config: RunnableConfig = {
            **config,
            "tags": [*(config.get("tags", [])), "node_route"],
        }
        prompt = cfg.prompt.format_messages(
            input=state.get_last_message(),
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt, config=node_config):
            tokens.append(str(chunk.content) or "")

        tags = "".join(tokens)
        log.info("Routing to: %s", tags)
        return {"payload": {**state.payload, "router_tags": tags}}

    return _route

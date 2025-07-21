"""orca_chat/skills/summarize.py"""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ..core.session import LLMSession
from ..loaders import LLMConfig


def build(llm: ChatOllama, cfg: LLMConfig) -> StateNode:
    async def _summarize(state: LLMSession, config: RunnableConfig) -> dict[str, Any]:
        node_config: RunnableConfig = {
            **config,
            "tags": [*(config.get("tags", [])), "out_silent"],
        }

        prompt = cfg.prompt.format_messages(
            chat_history=state.get_abridged_history(),
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt, config=node_config):
            tokens.append(str(chunk.content) or "")

        return {"payload": {**state.payload, "summary": "".join(tokens)}}

    return _summarize

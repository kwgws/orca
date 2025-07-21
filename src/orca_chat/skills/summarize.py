"""orca_chat/skills/summarize.py"""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ..config.load import SkillConfig
from ..core.session import LLMSession


def build(llm: ChatOllama, cfg: SkillConfig) -> StateNode:
    async def _summarize(state: LLMSession, config: RunnableConfig) -> dict[str, Any]:
        node_config: RunnableConfig = {
            **config,
            "tags": [*(config.get("tags", [])), "summarize_node"],
        }

        prompt = cfg.prompt.format_messages(
            chat_history=state.get_abridged_history(),
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt, config=node_config):
            tokens.append(str(chunk.content) or "")

        return {"payload": {**state.payload, "summary": "".join(tokens)}}

    return _summarize

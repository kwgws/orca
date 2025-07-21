"""orca_chat/skills/chat.py"""

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ..config.load import SkillConfig
from ..core.session import LLMSession, message_to_tuple


def build(llm: ChatOllama, cfg: SkillConfig) -> StateNode:
    async def _chat(state: LLMSession, config: RunnableConfig) -> dict[str, Any]:
        node_config: RunnableConfig = {
            **config,
            "tags": [*(config.get("tags", [])), "chat_node"],
        }

        prompt = cfg.prompt.format_messages(
            input=state.get_last_message(),
            chat_history=state.get_abridged_history(),
            context=state.get_context(),
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt, config=node_config):
            tokens.append(str(chunk.content) or "")

        ai_message = AIMessage("".join(tokens))
        return {"history": [*state.history, message_to_tuple(ai_message)]}

    return _chat

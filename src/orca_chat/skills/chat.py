"""orca_chat/skills/chat.py"""

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ..core.session import LLMSession, message_to_tuple
from ..loaders import LLMConfig


def build(llm: ChatOllama, cfg: LLMConfig) -> StateNode:
    async def _chat(state: LLMSession, config: RunnableConfig) -> dict[str, Any]:
        node_config: RunnableConfig = {
            **config,
            "tags": [*(config.get("tags", [])), "out_stream"],
        }

        prompt = cfg.prompt.format_messages(
            context=state.get_context(),
            chat_history=state.get_abridged_history(),
            input=state.get_last_message(),
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt, config=node_config):
            tokens.append(str(chunk.content) or "")

        ai_message = AIMessage("".join(tokens))
        return {"history": [*state.history, message_to_tuple(ai_message)]}

    return _chat

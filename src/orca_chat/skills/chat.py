"""orca_chat/skills/chat.py"""

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ..config.load import SkillConfig
from ..core.session import LLMSession


def build(llm: ChatOllama, cfg: SkillConfig) -> StateNode:
    async def _chat(state: LLMSession, config: RunnableConfig) -> BaseMessage | str:
        node_config: RunnableConfig = {
            **config,
            "tags": [*(config.get("tags", [])), "chat_node"],
        }

        prompt = cfg.prompt.format_messages(
            input=state.get_last_message(),
            chat_history=state.get_chat_history(),
            context=state.get_context(),
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt, config=node_config):
            token = str(chunk.content) or ""
            tokens.append(token)

        ai_message = AIMessage("".join(tokens))
        return ai_message

    return _chat

"""orca_chat/skills/chat.py"""

from dataclasses import dataclass
from typing import ClassVar, Final

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig

from ..core import LLMSkillMixin, Message, Session, Skill

__all__: Final = ["ChatSkill"]


@dataclass(slots=True, frozen=True)
class ChatSkill(LLMSkillMixin, Skill):
    name: ClassVar[str] = "chat"
    tags: ClassVar[frozenset] = frozenset({"chat", "llm", "stream"})
    llm_alias: ClassVar[str] = "llama3"

    async def __call__(self, state: Session, config: RunnableConfig) -> Session:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are an AI assistant."),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        ).format_messages(
            chat_history=state.get_history_abridged(),
            input=state.get_last_message(),
        )

        reply, metadata = await self._run_llm(prompt, config)
        state.history.append(Message("ai", reply, metadata=metadata))
        return state

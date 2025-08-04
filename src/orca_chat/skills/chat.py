# orca_chat/skills/llm/chat.py

from dataclasses import dataclass
from typing import ClassVar, Final

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig

from ..core import LLMSkillMixin, Message, Session, Skill

__all__: Final = ["ChatSkill"]

_SYSTEM = """
You are an AI assistant.
You have access to the following tool:

- `word_count(text: str)` -> {{ "word_count": n }}
  - Returns how many words are in `text`.

**When to use the tool**
- Anytime the user asks for a word count.
"""


@dataclass(slots=True, frozen=True)
class ChatSkill(LLMSkillMixin, Skill):
    name: ClassVar[str] = "chat"
    tags: ClassVar[frozenset] = frozenset({"chat", "llm", "skill", "stream"})
    llm_alias: ClassVar[str] = "llama3"

    async def __call__(self, state: Session, config: RunnableConfig) -> Session:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _SYSTEM),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        ).format_messages(
            chat_history=state.get_history_abridged(),
            input=state.input,
        )

        reply, metadata = await self._run_llm(prompt, config)
        state.history.append(Message("ai", str(reply.content), metadata=metadata))
        return state

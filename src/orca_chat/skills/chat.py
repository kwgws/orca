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
    tags: ClassVar[frozenset] = frozenset({"llm", "stream", name})
    llm_alias: ClassVar[str] = "llama3"

    async def __call__(self, state: Session, config: RunnableConfig) -> Session:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are an AI assistant."),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        ).format_messages(
            chat_history=[msg.as_tuple() for msg in state.get_history_abridged()],
            input=state.get_last_message(),
        )

        cfg: RunnableConfig = {**config, "tags": [*config.get("tags", []), *self.tags]}
        run = (
            self.llm.with_config(callbacks=cfg.pop("callbacks", None))
            if "callbacks" in cfg
            else self.llm
        )

        chunks: list[str] = []
        async for chunk in run.astream(prompt, config=cfg):
            chunks.append(str(chunk.content) or "")

        return state.with_message(Message("ai", "".join(chunks)))

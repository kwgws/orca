"""orca_chat/skills/summarize.py"""

from dataclasses import dataclass
from typing import ClassVar, Final

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig

from ..core import LLMSkillMixin, Session, Skill

__all__: Final = ["SummarizeSkill"]


@dataclass(slots=True, frozen=True)
class SummarizeSkill(LLMSkillMixin, Skill):
    """Summarize the conversation and store it in the session payload."""

    name: ClassVar[str] = "summarize"
    tags: ClassVar[frozenset] = frozenset({"llm", "stream", name})
    llm_alias: ClassVar[str] = "llama3"

    async def __call__(self, state: Session, config: RunnableConfig) -> Session:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are an AI assistant."),
                MessagesPlaceholder("chat_history"),
                ("human", "Summarize the conversation so far in no more than a paragraph."),
            ]
        ).format_messages(
            chat_history=[msg.as_tuple() for msg in state.get_history_abridged()],
        )

        cfg: RunnableConfig = {
            **config,
            "tags": [*config.get("tags", []), *self.tags],
        }
        run = (
            self.llm.with_config(callbacks=cfg.pop("callbacks", None))
            if "callbacks" in cfg
            else self.llm
        )

        chunks: list[str] = []
        async for chunk in run.astream(prompt, config=cfg):
            chunks.append(str(chunk.content) or "")

        summary = "".join(chunks).strip()
        return state.with_payload(summary=summary)

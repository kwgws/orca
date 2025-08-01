"""orca_chat/skills/chat.py"""

from typing import Any, cast

from langchain.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.runnables import RunnableConfig

from ..core import Message, Node, Session

__all__ = ["build_node"]

NAME = "chat"
TAGS = {"llm", "stream", NAME}


def build_node(llm: BaseChatModel, **_: Any):
    async def _factory(state: Session, config: RunnableConfig) -> Session:
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

        cfg: RunnableConfig = {
            **config,
            "tags": [*(config.get("tags", [])), *TAGS],
        }
        run = llm
        if "callbacks" in cfg:
            run = cast(BaseChatModel, llm.with_config(callbacks=cfg.pop("callbacks")))

        chunks: list[str] = []
        async for chunk in run.astream(prompt, config=cfg):
            chunks.append(str(chunk.content) or "")

        return state.with_message(Message("ai", "".join(chunks)))

    return Node(
        name=NAME,
        factory=_factory,
        tags=frozenset(TAGS),
    )

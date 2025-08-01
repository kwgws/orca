"""orca_chat/skills/chat.py"""

from typing import Any, Final, cast

from langchain.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.runnables import RunnableConfig

from ..core import Message, Node, Session

__all__: Final = ["build_node"]

NAME: Final = "chat"
TAGS: Final = {"llm", "stream", NAME}
LLM_ALIAS: Final = "llama3"


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

    return Node(NAME, _factory, tags=frozenset(TAGS), llm_alias=LLM_ALIAS)

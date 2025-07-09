from dataclasses import dataclass, field
from typing import Annotated

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

__all__ = ["ChatState"]


@dataclass
class ChatState:
    chat_history: Annotated[list[BaseMessage], add_messages] = field(
        default_factory=list, metadata={"reducer": add_messages}
    )
    summary: str | None = None
    router_flags: str | None = None
    search_query: str | None = None
    documents: list[Document] | None = None

    def question(self) -> str:
        for message in reversed(self.chat_history):
            if message.type == "human":
                return str(message.content)
        return ""

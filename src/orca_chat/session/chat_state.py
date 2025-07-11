from dataclasses import dataclass, field
from typing import Annotated

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


@dataclass(slots=True)
class ChatState:
    """Container for maintaining chat context and metadata.

    Attributes
    ----------
    chat_history : list of BaseMessage
        List of messages exchanged in the conversation.
    summary : str, optional
        Summary of the conversation, if available.
    router_flags : str, optional
        Optional flags used to route or tag conversation state.
    search_query : str, optional
        Optional search query derived from the conversation.
    documents : list of Document, optional
        Related documents retrieved or referenced during the conversation.
    chat_history: Annotated[list[BaseMessage], add_messages] = field(
        default_factory=list, metadata={"reducer": add_messages}
    """

    chat_history: Annotated[list[BaseMessage], add_messages] = field(
        default_factory=list, metadata={"reducer": add_messages}
    )
    summary: str | None = None
    router_flags: str | None = None
    search_query: str | None = None
    documents: list[Document] | None = None

    @property
    def question(self) -> str:
        """The most recent human message."""
        for message in reversed(self.chat_history):
            if message.type == "human":
                return str(message.content)
        return ""

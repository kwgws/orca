from dataclasses import dataclass, field, replace
from typing import Any, Self

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage

_DOCUMENT_MAX_CHARS = 4_000
_DOCUMENT_MAX_PRINT = 3
_DOCUMENT_PRINT_TEMPLATE = """
- [{index}]({source}): {text}
"""


@dataclass(slots=True)
class ChatState:
    """Container for maintaining chat context and metadata.

    Attributes
    ----------
    question : str
        The most recent human message.
    disambiguation : str
        Last user question, rewritten for clarity.
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
    """

    question: str = ""
    disambiguation: str | None = None
    chat_history: list[BaseMessage] = field(default_factory=list)
    summary: str | None = None
    router_flags: str | None = None
    search_query: str | None = None
    documents: list[Document] | None = None

    def get_documents_str(
        self,
        *,
        max_chars=_DOCUMENT_MAX_CHARS,
        max_documents=_DOCUMENT_MAX_PRINT,
        template=_DOCUMENT_PRINT_TEMPLATE,
        doc_list: list[Document] | None = None,
    ) -> str:
        docs = doc_list or self.documents or []
        return "\n".join(
            [
                template.format(
                    index=i,
                    source=doc.metadata.get("source") or "unknown",
                    text=(doc.metadata.get("summary") or doc.page_content.strip())[:max_chars],
                )
                for i, doc in enumerate(docs[:max_documents])
            ]
        )

    def merge(self, params: dict[str, Any]) -> Self:
        return replace(self, **params)

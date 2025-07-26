"""orca_chat/core/session.py"""

import asyncio
import json
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Self, overload

from langchain_core.documents import Document
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from ..loaders import load_config

# ...
Predicate = Callable[["ChatSession"], bool]

# ...
_CONFIG = load_config()
_DOC_FORMAT_STR: str = _CONFIG.llm.doc_format_str
_MAX_DOC_LENGTH: int = _CONFIG.llm.max_doc_length
_MAX_DOCS: int = _CONFIG.llm.max_docs
_MAX_ROUNDS: int = _CONFIG.llm.max_chat_rounds_to_llm

# ...
_MSG_TYPE_MAP: dict[str, type[BaseMessage]] = {
    "system": SystemMessage,
    "ai": AIMessage,
    "assistant": AIMessage,
    "tool": ToolMessage,
    "human": HumanMessage,
    "user": HumanMessage,
}


def tuple_to_message(role: str, content: str) -> BaseMessage:
    """Return :class:`BaseMessage` from ``role`` and ``content``."""
    try:
        cls = _MSG_TYPE_MAP[role.lower()]
        return cls(content=content)
    except KeyError as e:
        role_list = "[" + ", ".join(f"'{k}'" for k in _MSG_TYPE_MAP.keys()) + "]"
        raise ValueError(f"Role '{role}' does not match any of {role_list}") from e


def message_to_tuple(msg: BaseMessage) -> tuple[str, str]:
    """Return ``(role, content)`` from :class:`BaseMessage`."""
    return msg.type.lower(), str(msg.content)


@dataclass(slots=True)
class ChatSession:
    """Container for chat history and arbitrary payload data.

    Parameters
    ----------
    history
        Chronological ``(role, content)`` pairs. Role names follow the
        LangChain convention.
    payload
        Additional JSON-serializable data.
    """

    history: list[tuple[str, str]] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def as_messages(self) -> list[BaseMessage]:
        """Return ``history`` as :class:`BaseMessage` instances."""
        return [tuple_to_message(r, c) for r, c in self.history]

    @classmethod
    def from_messages(cls, messages: Sequence[BaseMessage], **payload: Mapping[str, Any]) -> Self:
        """Create session from sequence of :class:`BaseMessage`."""
        return cls(history=[message_to_tuple(msg) for msg in messages], payload=dict(payload))

    @classmethod
    def from_state(cls, state: Mapping[str, Any]) -> Self:
        """Create session from raw state mapping."""
        return cls(**state)

    def get_last_message(self, *, roles: tuple[str, ...] = ("human",), use_disambiguation=True):
        """Return most recent message as tuple matching ``roles``."""
        for role, content in reversed(self.history):
            if role not in roles:
                continue
            if role in {"human", "user"} and use_disambiguation:
                return self.payload.get("disambiguation", "") or content
            return content
        return ""

    def get_abridged_history(self) -> list[BaseMessage]:
        """Return conversation history excluding last message."""
        history = self.as_messages()[-_MAX_ROUNDS * 2 : -1]
        if summary := self.payload.get("summary"):
            history = [AIMessage(summary), *history]
        return history

    def get_documents(
        self,
        *,
        max_docs: int | None = _MAX_DOCS,
        max_doc_length: int | None = _MAX_DOC_LENGTH,
        prefer_summary=False,
    ) -> str:
        """Return document list as string from payload."""
        docs: list[Document] = self.payload.get("documents", [])
        if not docs:
            return ""
        if max_docs and max_docs > 0:
            docs = docs[:max_docs]

        documents: list[str] = []
        for i, doc in enumerate(docs):
            content = (
                doc.metadata.get("summary") or doc.page_content
                if prefer_summary
                else doc.page_content
            )
            if max_doc_length and max_doc_length > 0:
                content = content[:max_doc_length]
            documents.append(
                _DOC_FORMAT_STR.format(
                    index=i,
                    source=doc.metadata.get("source", "<unknown>"),
                    content=doc.page_content,
                )
            )
        return "\n\n\n---\n\n\n".join(documents)

    @overload
    def with_message(self, msg: tuple[str, str]) -> Self: ...

    @overload
    def with_message(self, msg: BaseMessage) -> Self: ...

    def with_message(self, msg) -> Self:
        """Copy session with ``msg`` appended to history."""
        role, content = msg if isinstance(msg, tuple) else message_to_tuple(msg)
        new_history = [*self.history, (role, content)]
        return replace(self, history=new_history)

    def with_payload(self, **kwargs: Any) -> Self:
        """Copy session with updated payload values."""
        new_payload: MutableMapping[str, Any] = {**self.payload, **kwargs}
        return replace(self, payload=new_payload)

    async def save(self, path: str | Path) -> None:
        """Write session to ``path`` as JSON."""
        path = Path(path)
        await asyncio.to_thread(path.write_text, json.dumps(asdict(self), indent=2))

    @classmethod
    async def load(cls, path: str | Path) -> Self:
        """Load session from ``path`` written by :meth:`save`."""
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)

        raw = await asyncio.to_thread(path.read_text)
        data: Mapping[str, Any] = json.loads(raw)

        return cls(
            history=[tuple(msg) for msg in data.get("history", [])],
            payload=data.get("payload", {}),
        )

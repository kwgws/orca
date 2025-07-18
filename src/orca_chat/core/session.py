"""orca_chat/core/session.py"""

import asyncio
import json
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Self, overload

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

_MSG_TYPE_MAP: dict[str, type[BaseMessage]] = {
    "system": SystemMessage,
    "ai": AIMessage,
    "assistant": AIMessage,
    "tool": ToolMessage,
    "human": HumanMessage,
    "user": HumanMessage,
}

History = list[tuple[str, str]]


def tuple_to_lcmessage(role: str, content: str) -> BaseMessage:
    """Return :class:`BaseMessage` from ``role`` and ``content`` strings."""
    try:
        cls = _MSG_TYPE_MAP[role.lower()]
        return cls(content=content)
    except KeyError as e:
        role_list = "[" + ", ".join(f"'{k}'" for k in _MSG_TYPE_MAP.keys()) + "]"
        raise ValueError(f"Role '{role}' does not match any of {role_list}") from e


def lcmessage_to_tuple(msg: BaseMessage) -> tuple[str, str]:
    """Return string tuple from :class:`BaseMessage`"""
    return msg.type.lower(), str(msg.content)


@dataclass(slots=True)
class LLMSession:
    """Immutable-by-default session state.

    Attributes
    ----------
    history : History
        Chronological list of ``(role, content)`` tuples. Roles follow
        LangChain's lowercase convention (``"system"``, ``"human"``,
        ``"ai"``/``"assistant"``, ``"tool"``).
    payload : dict
        Miscellaneous per-conversation data (embedding cache, context, etc.).
        Values must be JSON-serializable.
    """

    history: History = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def as_lcmessages(self) -> list[BaseMessage]:
        """Return ``history`` as :class:`BaseMessage` objects."""
        return [tuple_to_lcmessage(r, c) for r, c in self.history]

    @classmethod
    def from_lcmessages(cls, messages: Sequence[BaseMessage], **payload: Mapping[str, Any]) -> Self:
        """Instantiate :class:`LLMSession` from :class:`BaseMessage` objects."""
        return cls(history=[lcmessage_to_tuple(msg) for msg in messages], payload=dict(payload))

    @classmethod
    def from_state(cls, state: Mapping[str, Any]) -> Self:
        return cls(**state)

    def get_last_message(self, *, roles: tuple[str, ...] = ("human",)):
        for role, content in reversed(self.history):
            if role in roles:
                return content
        return ""

    def get_chat_history(self) -> list[BaseMessage]:
        return self.as_lcmessages()[:-1]

    def get_context(self) -> str:
        return self.payload.get("context", "")

    @overload
    def with_message(self, msg: tuple[str, str]) -> Self: ...

    @overload
    def with_message(self, msg: BaseMessage) -> Self: ...

    def with_message(self, msg) -> Self:
        """Return new :class:`LLMSession` with ``msg`` appended to history."""
        role, content = msg if isinstance(msg, tuple) else lcmessage_to_tuple(msg)
        new_history = [*self.history, (role, content)]
        return replace(self, history=new_history)

    def with_payload(self, **kwargs: Any) -> Self:
        """Return new :class:`LLMSession` with ``kwargs`` shallow-merged with ``payload``."""
        new_payload: MutableMapping[str, Any] = {**self.payload, **kwargs}
        return replace(self, payload=new_payload)

    async def save(self, path: str | Path) -> None:
        """Serialize to ``path`` as JSON."""
        path = Path(path)
        await asyncio.to_thread(path.write_text, json.dumps(asdict(self), indent=2))

    @classmethod
    async def load(cls, path: str | Path) -> Self:
        """Deserialize from JSON string stored as ``path``."""
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)

        raw = await asyncio.to_thread(path.read_text)
        data: Mapping[str, Any] = json.loads(raw)

        return cls(
            history=[tuple(msg) for msg in data.get("history", [])],
            payload=data.get("payload", {}),
        )

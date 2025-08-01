"""orca_chat/core/message.py"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final, Self
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

__all__: Final = ["Message"]


RE_WHITESPACE: Final = re.compile(r"\s+")
"""Match all whitespace (incl. newlines, tabs)."""

ROLE_TO_TYPE_MAP: Final[dict[str, type[AIMessage | HumanMessage | SystemMessage | ToolMessage]]] = {
    "ai": AIMessage,
    "human": HumanMessage,
    "system": SystemMessage,
    "tool": ToolMessage,
}
"""Mapping of *role* strings to concrete *LangChain* message classes."""


@dataclass(slots=True, frozen=True)
class Message:
    """Immutable chat message.

    Parameters
    ----------
    role
        The logical speaker of this message; must match langchain types.
    content
        Raw text payload.
    msg_id
        Unique identifier (hex=encoded UUID4).
    timestamp
        Creation time as UTC-aware :class:`datetime`.
    """

    role: str
    content: str
    msg_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        # Double-check role against langchain message type literals.
        if self.role not in ROLE_TO_TYPE_MAP:
            raise ValueError(f"Invalid message role: '{self.role}'")

    # - - - - - - - - - - - - - - - -
    # Constructors
    # - - - - - - - - - - - - - - - -

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        **kwargs: Any,
    ) -> Self:
        """Build a :class:`Message` from a JSON-serialised mapping.

        Unknown keys are ignored, additional keyword arguments override their
        counterparts from *data*.

        Raises
        ------
        ValueError
            If mandatory fields are missing or cannot be parsed.
        """
        try:
            params = {"role": data["role"], "content": data["content"]}
            if "msg_id" in data:
                params["msg_id"] = data["msg_id"]
            if "timestamp" in data:
                params["timestamp"] = datetime.fromisoformat(data["timestamp"])
            return cls(**params | kwargs)
        except (KeyError, ValueError) as e:
            raise ValueError("Could not parse message") from e

    @classmethod
    def from_message(
        cls,
        msg: AIMessage | HumanMessage | SystemMessage | ToolMessage,
        **kwargs: Any,
    ) -> Self:
        """Create from an existing langchain message instance."""
        return cls(role=msg.type, content=str(msg.content), **kwargs)

    @classmethod
    def from_tuple(
        cls,
        msg: tuple[str, str],
        **kwargs,
    ) -> Self:
        """Create from tuple ``(role, content)``."""
        return cls(*msg, **kwargs)

    # - - - - - - - - - - - - - - - -
    # Interfaces
    # - - - - - - - - - - - - - - - -

    def get_content(self, *, trim=False, max_chars: int | None = None) -> str:
        """Return *content* with optional whitespace normalization & cropping.

        This is especially useful for logging or other cases where a short
        version of the content string might be needed.

        Parameters
        ----------
        trim
            When *True* collapse all whitespace into single spaces.
        max_chars
            Truncate to this many characters (+ ellipsis) when provided.
        """
        content = self.content
        if trim:
            content = RE_WHITESPACE.sub(" ", content)
        if max_chars and len(self.content) > max_chars > 0:
            content = content[:max_chars] + "..."
        return content

    # - - - - - - - - - - - - - - - -
    # Serializers
    # - - - - - - - - - - - - - - - -

    def as_dict(self) -> dict[str, str]:
        """Serialize to a JSON-friendly ``dict``."""
        return {
            "msg_id": self.msg_id,
            "timestamp": self.timestamp.isoformat(),
            "role": self.role,
            "content": self.content,
        }

    def as_message(self) -> AIMessage | HumanMessage | SystemMessage | ToolMessage:
        """Convert to the corresponding langchain message class."""
        cls = ROLE_TO_TYPE_MAP[self.role.lower()]
        return cls(content=self.content)

    def as_tuple(self) -> tuple[str, str]:
        """Return ``(role, content)`` tuple."""
        return (self.role, self.content)

# orca_chat/core/session.py

import asyncio
import json
from collections.abc import Mapping, Set
from dataclasses import dataclass, field
from typing import Any, Final, Self
from uuid import uuid4

from langchain_core.messages import BaseMessage

from .message import Message

__all__: Final = ["DEFAULT_MAX_ROUNDS", "Session", "SessionStore"]

DEFAULT_MAX_ROUNDS: Final[int] = 6


@dataclass(slots=True, frozen=True)
class Session:
    """Immutable container for conversation state.

    Parameters
    ----------
    session_id
        Unique hex-encoded UUID4 generated on demand.
    history
        Ordered list of :class:`Message` objects.
    payload
        Arbitrary key/value store for *derived* data (eg summaries,
        embeddings, sentiment scores, user metadata, etc).
    """

    session_id: str = field(default_factory=lambda: uuid4().hex)
    history: list[Message] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    # - - - - - - - - - - - - - - - -
    # Constructors
    # - - - - - - - - - - - - - - - -

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], **kwargs: Any) -> Self:
        """Re-hydrate from a JSON-like mapping.

        Unknown keys are ignored; explicit *kwargs* win over *data*. Raises
        :class:`ValueError` when mandatory fields are missing or malformed.
        """
        params: dict[str, Any] = {}

        try:
            if isinstance(data.get("session_id"), str):
                params["session_id"] = data["session_id"]

            if isinstance(data.get("history"), list | tuple):
                history = data["history"]
                if isinstance(history[0], dict):
                    params["history"] = [Message.from_dict(msg) for msg in history]
                elif isinstance(history[0], list | tuple):
                    params["history"] = [Message(r, c) for r, c in history]

            if isinstance(data.get("payload"), dict):
                params["payload"] = data["payload"]

            return cls(**params | kwargs)

        except (KeyError, ValueError, TypeError) as e:
            raise ValueError("Could not parse session dict") from e

    @classmethod
    def from_json(cls, json_str: str, **kwargs: Any) -> Self:
        """Parse from a raw JSON string."""
        try:
            return cls.from_dict(json.loads(json_str), **kwargs)
        except (ValueError, json.JSONDecodeError) as e:
            raise ValueError("Could not parse session JSON") from e

    # - - - - - - - - - - - - - - - -
    # Interfaces
    # - - - - - - - - - - - - - - - -

    def get_history(
        self,
        *,
        drop_input=False,
    ) -> list[Message]:
        """Entire chat log, optionally hiding the last human turn.

        Parameters
        ----------
        drop_input
            Use when you do *not* see the user's current question again (e.g.
            because it is being provided to the LLM as ``input``).
        """
        if self.history and drop_input and self.history[-1].role == "human":
            return list(self.history[:-1])
        return list(self.history)

    def get_history_abridged(
        self,
        max_rounds=DEFAULT_MAX_ROUNDS,
        *,
        drop_input=True,
    ) -> list[BaseMessage]:
        """Abridged chat log formatted as a list of :class:`BaseMessage`.

        When a *summary* exists in *payload*, it is prepended as the oldest
        AI message so the model keeps the gist of older turns.

        Parameters
        ----------
        max_rounds
            Returns at most this many (human+AI) pairs.
        drop_input
            Use when you do *not* see the user's current question again (e.g.
            because it is being provided to the LLM as ``input``).
        """
        history = self.get_history(drop_input=drop_input)[-max_rounds * 2 :]
        if summary := self.payload.get("summary"):
            history = [Message("ai", summary), *history]
        return [msg.as_message() for msg in history]

    def get_last_message(self, roles: Set[str] = {"human"}) -> Message:
        """Return *content* of the last message whose role matches *roles*.

        If no matches are found, an empty string is returned.
        """
        for msg in reversed(self.history):
            if msg.role not in roles:
                continue
            return msg
        raise ValueError(f"No messages in session with roles: {roles}")

    @property
    def input(self) -> str:
        """Content of last user message, if any."""
        return self.get_last_message({"human"}).as_str()

    # - - - - - - - - - - - - - - - -
    # Serializers
    # - - - - - - - - - - - - - - - -

    def as_dict(self) -> dict[str, Any]:
        """Return as a JSON-friendly dict mapping."""
        return {
            "session_id": self.session_id,
            "history": [msg.as_dict() for msg in self.history],
            "payload": self.payload,
        }

    def as_json(self, **kwargs: Any) -> str:
        """Return as a raw JSON string."""
        return json.dumps(self.as_dict(), **kwargs)


@dataclass(slots=True)
class SessionStore:
    """In-memory mapping of *session_id* to :class:`Session`."""

    _store: dict[str, Session] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def put(self, session: Session) -> None:
        async with self._lock:
            self._store[session.session_id] = session

    async def get(self, session_id: str) -> Session | None:
        async with self._lock:
            return self._store.get(session_id)

    async def delete(self, session_id: str) -> None:
        async with self._lock:
            self._store.pop(session_id, None)

    async def all(self) -> list[Session]:
        async with self._lock:
            return [s for s in self._store.values()]

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

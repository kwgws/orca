"""Shared state structures for the chat controller."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto

from langchain_core.chat_history import InMemoryChatMessageHistory

log = logging.getLogger(__name__)


class ChatStage(Enum):
    """Discrete states in the chat flow."""

    AWAITING_INPUT = auto()
    STARTED_STREAM = auto()
    STARTED_PRECIS = auto()


@dataclass(slots=True)
class SessionState:
    """Lightweight container for per-session state."""

    history: InMemoryChatMessageHistory = field(default_factory=InMemoryChatMessageHistory)
    precis: str = ""


@dataclass(slots=True)
class StageTracker:
    """Keep track of the current :class:`ChatStage` for each session."""

    _stages: dict[str, ChatStage] = field(default_factory=dict)

    def set(self, session_id: str, stage: ChatStage) -> None:
        """Record ``stage`` for ``session_id`` and log the transition."""
        self._stages[session_id] = stage
        log.debug("Set stage [%s]: %s", session_id, stage.name)

    def get(self, session_id: str) -> ChatStage:
        """Return the most recent stage for ``session_id``."""
        return self._stages.get(session_id, ChatStage.AWAITING_INPUT)

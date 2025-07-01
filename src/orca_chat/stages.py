"""Lightweight state tracking for chat sessions."""

import logging
from enum import Enum, auto

logger = logging.getLogger(__name__)


class ChatStage(Enum):
    """Discrete states in the chat flow."""

    WAITING_FOR_USER = auto()
    SENDING_TO_MODEL = auto()
    STREAM_FROM_CHAT = auto()
    SUMMARIZING_CHAT = auto()


class StageTracker:
    """Keep track of the current :class:`ChatStage` for each session."""

    def __init__(self) -> None:
        self._stages: dict[str, ChatStage] = {}

    def set(self, session_id: str, stage: ChatStage) -> None:
        """Record ``stage`` for ``session_id`` and log the transition."""
        self._stages[session_id] = stage
        logger.info("[stage → %s]: %s", session_id, stage.name)

    def get(self, session_id: str) -> ChatStage:
        """Return the most recent stage for ``session_id``."""
        return self._stages.get(session_id, ChatStage.WAITING_FOR_USER)

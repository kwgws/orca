"""Lightweight state tracking for :class:`ChatController`"""

import logging
from enum import Enum, auto

log = logging.getLogger(__name__)


class ChatStage(Enum):
    """Discrete states in the chat flow."""

    AWAITING_INPUT = auto()
    STARTED_STREAM = auto()
    STARTED_PRECIS = auto()


class StageTracker:
    """Keep track of the current :class:`ChatStage` for each session."""

    def __init__(self) -> None:
        self._stages: dict[str, ChatStage] = {}

    def set(self, session_id: str, stage: ChatStage) -> None:
        """Record ``stage`` for ``session_id`` and log the transition."""
        self._stages[session_id] = stage
        log.debug("Set stage [%s]: %s", session_id, stage.name)

    def get(self, session_id: str) -> ChatStage:
        """Return the most recent stage for ``session_id``."""
        return self._stages.get(session_id, ChatStage.AWAITING_INPUT)

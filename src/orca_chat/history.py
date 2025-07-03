"""Deprecated module kept for backward compatibility."""

from __future__ import annotations

from langchain_core.chat_history import InMemoryChatMessageHistory

from .state import SessionState

__all__ = ["InMemoryChatMessageHistory", "SessionState"]

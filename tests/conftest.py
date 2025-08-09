# tests/conftest.py

from collections.abc import Iterable
from typing import Final

import pytest
from langchain_core.language_models.fake_chat_models import (
    FakeMessagesListChatModel,
)
from langchain_core.messages import BaseMessage

__all__: Final = [
    "llm_stub",
]


@pytest.fixture
def llm_stub(monkeypatch):
    """Factory fixture to install a :class:`FakeMessagesListChatModel` and
    patch :meth:`get_llm`.

    Example
    -------
    >>> fake = llm_stub(
    ...     responses=[AIMessage(...), ...],
    ...     targets=[
    ...         "orca_chat.skills.route.get_llm",
    ...         ...,
    ...     ],
    >>> )
    """

    def _install(
        *,
        responses: list[BaseMessage],
        targets: Iterable[str] = (
            "orca_chat.skills.route.get_llm",
            "orca_chat.skills.chat.get_llm",
            "orca_chat.skills.summarize.get_llm",
        ),
    ) -> FakeMessagesListChatModel:
        fake = FakeMessagesListChatModel(responses=responses)

        async def fake_get_llm(**_):
            return fake

        for target in targets:
            monkeypatch.setattr(target, fake_get_llm)
        return fake

    return _install

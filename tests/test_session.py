"""tests/test_session.py"""

import pytest

from orca_chat.core.session import ChatSession


@pytest.mark.asyncio
async def test_session_serialization(tmp_path):
    session = ChatSession().with_message(("human", "hello"))
    file = tmp_path / "session.json"
    await session.save(file)
    loaded = await ChatSession.load(file)
    assert loaded == session


def test_session_immutable():
    session = ChatSession()
    new = session.with_message(("human", "hello"))
    assert session.history == []
    assert new.history == [("human", "hello")]

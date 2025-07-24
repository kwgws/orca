"""tests/test_session.py"""

import pytest

from orca_chat.core.session import ChatSession, tuple_to_message


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


def test_invalid_role():
    with pytest.raises(ValueError):
        tuple_to_message("bad", "msg")


def test_get_last_msg():
    session = ChatSession().with_message(("human", "hi")).with_message(("assistant", "yo"))
    assert session.get_last_message(roles=("assistant",)) == "yo"
    assert session.get_last_message(roles=("human",)) == "hi"
    assert ChatSession().get_last_message() == ""

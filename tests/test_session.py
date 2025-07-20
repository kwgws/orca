import pytest

from orca_chat.core.session import LLMSession


@pytest.mark.asyncio
async def test_session_serialization(tmp_path):
    session = LLMSession().with_message(("human", "hello"))
    file = tmp_path / "session.json"
    await session.save(file)
    loaded = await LLMSession.load(file)
    assert loaded == session


def test_session_immutable():
    session = LLMSession()
    new = session.with_message(("human", "hello"))
    assert session.history == []
    assert new.history == [("human", "hello")]

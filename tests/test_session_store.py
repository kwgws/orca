from pathlib import Path

import pytest

from orca_chat.core.session_store import SessionStore


@pytest.mark.asyncio
async def test_session_store_roundtrip(tmp_path: Path) -> None:
    store = SessionStore(directory=tmp_path)
    session_id, session = await store.create()
    session = session.with_message(("human", "hi"))
    await store.save(session_id, session)
    loaded = await store.load(session_id)
    assert loaded == session
    assert session_id in store.list_ids()

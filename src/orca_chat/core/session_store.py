"""orca_chat/core/session_store.py"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from .session import ChatSession


@dataclass(slots=True)
class SessionHandle:
    """Reference to a stored :class:`ChatSession`."""

    store: "SessionStore"
    session_id: str
    session: ChatSession

    async def update(self, session: ChatSession) -> ChatSession:
        """Persist ``session`` and return it."""
        self.session = await self.store.update(self.session_id, session)
        return self.session

    async def with_message(self, msg: tuple[str, str]) -> ChatSession:
        """Append ``msg`` and persist session."""
        new_session = self.session.with_message(msg)
        return await self.update(new_session)


@dataclass(slots=True)
class SessionStore:
    """Manage serialized :class:`ChatSession` objects in a directory."""

    directory: Path = Path("./sessions")
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)

    def list_ids(self) -> list[str]:
        """Return all known session identifiers."""
        ids = [path.stem for path in self.directory.glob("*.json")]
        return sorted(ids)

    def path_for(self, session_id: str) -> Path:
        """Return filesystem path for ``session_id``."""
        return self.directory / f"{session_id}.json"

    async def create(self) -> tuple[str, ChatSession]:
        """Create a new session and return its id and object."""
        session_id = uuid4().hex
        session = ChatSession()
        await self.save(session_id, session)
        return session_id, session

    async def open(self, session_id: str | None = None) -> SessionHandle:
        """Return a managed session, creating it if missing."""
        if session_id is None:
            session_id, session = await self.create()
        elif session_id in self:
            session = await self.load(session_id)
        else:
            session = ChatSession()
            await self.save(session_id, session)
        return SessionHandle(self, session_id, session)

    async def save(self, session_id: str, session: ChatSession) -> Path:
        """Write ``session`` to disk."""
        path = self.path_for(session_id)
        async with self._lock:
            await session.save(path)
        return path

    async def load(self, session_id: str) -> ChatSession:
        """Load ``session_id`` from disk."""
        return await ChatSession.load(self.path_for(session_id))

    async def update(self, session_id: str, session: ChatSession) -> ChatSession:
        """Persist and return ``session``."""
        await self.save(session_id, session)
        return session

    def __len__(self):
        return len(self.list_ids())

    def __iter__(self):
        yield from self.list_ids()

    def __contains__(self, session_id: str):
        return self.path_for(session_id).exists()

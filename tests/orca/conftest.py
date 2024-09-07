import pytest_asyncio

from orca.model import Base, get_async_engine, get_async_session, init_async_engine


@pytest_asyncio.fixture(scope="function")
async def session():
    await init_async_engine("sqlite+aiosqlite:///:memory:")
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with get_async_session() as session:
        yield session
    await engine.dispose()

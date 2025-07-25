"""orca_chat/interfaces/cli.py"""

import asyncio
from collections.abc import AsyncIterator

from langchain_core.runnables import RunnableConfig

from ..core import ChatSession, SessionHandle, SessionStore, SkillStore
from ..loaders import load_logger
from .callbacks import JSONWriter, LogWriter, StdoutWriter


async def _yield_user_input() -> AsyncIterator[str]:
    loop = asyncio.get_running_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, lambda: input("> "))
        except EOFError:
            break
        if line.strip().lower() in {"/exit", "/quit", "/bye"}:
            break
        yield line


async def _chat_loop(handle: SessionHandle) -> None:
    skill_store = SkillStore()
    graph = await skill_store.get_graph("default")
    config: RunnableConfig = {"callbacks": [LogWriter(), JSONWriter(), StdoutWriter()]}

    async for user_msg in _yield_user_input():
        await handle.with_message(("human", user_msg))
        result = await graph.ainvoke(handle.session, config)
        await handle.update(ChatSession.from_state(result))


async def _main_async() -> None:
    load_logger()
    store = SessionStore()
    handle = await store.open()
    await _chat_loop(handle)


def run() -> None:
    """Start interactive REPL client."""
    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        print()

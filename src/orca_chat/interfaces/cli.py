import asyncio
from collections.abc import AsyncIterator

from langchain_core.runnables import RunnableConfig

from ..config.load import load_logger
from ..core.registry import LLMRegistry
from ..core.session import LLMSession
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


async def _chat_loop(session: LLMSession) -> None:
    registry = LLMRegistry()
    graph = await registry.get_graph("default")
    config: RunnableConfig = {"callbacks": [LogWriter(), JSONWriter(), StdoutWriter()]}

    async for user_msg in _yield_user_input():
        session = session.with_message(("human", user_msg))
        result = await graph.ainvoke(session, config)
        session = LLMSession.from_state(result)


async def _main_async() -> None:
    load_logger()
    session = LLMSession()
    await _chat_loop(session)


def run() -> None:
    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        print()

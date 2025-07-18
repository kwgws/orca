import asyncio
import textwrap
from collections.abc import AsyncIterator

from ..config.load import load_logger
from ..core.registry import LLMRegistry
from ..core.session import LLMSession


def _wrap_text(text: str, width=80) -> list[str]:
    return textwrap.wrap(text, width=width, replace_whitespace=False)


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


async def chat_loop(session: LLMSession) -> None:
    registry = LLMRegistry()
    graph = await registry.get_graph("default")

    async for user_msg in _yield_user_input():
        session = session.with_message(("human", user_msg))
        result = await graph.ainvoke(session)
        session = LLMSession.from_state(result)

        reply = session.get_last_message(roles=("ai", "assistant"))
        print("\n".join(_wrap_text(reply)))
        print()


async def _main_async() -> None:
    load_logger()
    session = LLMSession()
    await chat_loop(session)


def run() -> None:
    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        print()

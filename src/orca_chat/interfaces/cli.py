"""orca_chat/interfaces/cli.py"""

import asyncio
from collections.abc import AsyncIterator

from ..callbacks import StreamStdOut
from ..core import Message, Session
from ..graphs.default import build_graph_default


async def _yield_user_input() -> AsyncIterator[str]:
    loop = asyncio.get_running_loop()
    while True:
        try:
            msg = await loop.run_in_executor(None, lambda: input("\n> "))
            msg = msg.strip()
        except EOFError:
            break
        if msg.lower() in {"/exit", "/quit", "/bye"}:
            break
        yield msg


async def _chat_loop() -> None:
    graph = await build_graph_default()
    session = Session()
    async for msg in _yield_user_input():
        session.history.append(Message("human", msg))
        try:
            await graph.ainvoke(
                session,
                config={"callbacks": [StreamStdOut()]},
            )
        except asyncio.CancelledError:
            print("\nRequest cancelled.")
        except Exception:
            raise


def run() -> None:
    try:
        asyncio.run(_chat_loop())
    except KeyboardInterrupt:
        print("\nGoodbye!")

"""orca_chat/interfaces/cli.py"""

import asyncio
from collections.abc import AsyncIterator

from langchain_openai import ChatOpenAI

from ..core.callbacks import StreamStdOut

llm = ChatOpenAI(
    base_url="http://192.168.1.15:1234/v1",
    model="meta-llama-3.1-8b-instruct",
    streaming=True,
    callbacks=[StreamStdOut()],
)


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
    async for msg in _yield_user_input():
        try:
            await llm.ainvoke(msg)
        except asyncio.CancelledError:
            print("\nRequest cancelled.")


def run() -> None:
    try:
        asyncio.run(_chat_loop())
    except KeyboardInterrupt:
        print("\nGoodbye!")

"""Simple command line demo for :mod:`orca_chat`."""

import asyncio
import logging
import os

from orca_chat.config import LLMConfig, LLMRegistry
from orca_chat.controller import ChatController

logging.basicConfig(level=logging.INFO)

__all__ = ["demo"]


PROMPT = "Explain why the sky is blue."


def _build_registry() -> LLMRegistry:
    """Populate an :class:`LLMRegistry` from environment variables."""
    registry = LLMRegistry()

    chat_cfg = LLMConfig(
        model=os.environ.get("CHAT_MODEL_NAME", "chat"),
        temperature=0.7,
        base_url=os.environ.get("CHAT_MODEL_URL", "http://localhost:11434"),
    )
    registry.add(chat_cfg, "chat")

    summarizer_cfg = LLMConfig(
        model=os.environ.get("SUMMARIZER_MODEL_NAME", "summarizer"),
        temperature=0.2,
        base_url=os.environ.get("SUMMARIZER_MODEL_URL", "http://localhost:11434"),
    )
    registry.add(summarizer_cfg, "summarizer")

    return registry


async def demo() -> None:
    """Stream a single reply for ``PROMPT`` using the configured models."""
    registry = _build_registry()
    controller = ChatController(registry, default_alias="chat", summarizer_alias="summarizer")

    print(f"{PROMPT}\n")
    try:
        async for tok in controller.astream_reply("demo", PROMPT):
            print(tok, end="", flush=True)
    finally:
        print("\n\n")


if __name__ == "__main__":
    asyncio.run(demo())

"""Simple command line demo for :mod:`orca_chat`."""

import asyncio
import logging
import os

from orca_chat.config import LLMConfig, LLMRegistry
from orca_chat.controller import ChatController

handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
handler.setFormatter(formatter)

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(handler)

__all__ = ["demo"]


PROMPT = "Explain why the sky is blue."


def _build_registry() -> LLMRegistry:
    """Populate a :class:`LLMRegistry` from environment variables."""
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
    log = logging.getLogger(__name__)

    registry = _build_registry()
    controller = ChatController(registry, default_alias="chat", summarizer_alias="summarizer")

    log.info("Sending prompt: %s", PROMPT)
    async for token in controller.astream_reply("demo", PROMPT):
        print(token, end="", flush=True)

    log.info("Done!")


if __name__ == "__main__":
    asyncio.run(demo())

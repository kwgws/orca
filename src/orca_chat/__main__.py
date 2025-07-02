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


PROMPT = "Explain why the sky is blue."


def _build_registry() -> LLMRegistry:
    """Populate a :class:`LLMRegistry` from environment variables."""
    registry = LLMRegistry()

    cfg = LLMConfig(
        model=os.environ.get("LLM", "default"),
        temperature=0.7,
        base_url=os.environ.get("LLM_URL", "http://localhost:11434"),
    )
    registry.add(cfg, "default")

    editor_cfg = LLMConfig(
        model=os.environ.get("EDITOR_LLM", "precis"),
        temperature=0.2,
        base_url=os.environ.get("EDITOR_LLM_URL", "http://localhost:11434"),
    )
    registry.add(editor_cfg, "editor")

    return registry


async def demo() -> None:
    """Stream a single reply for ``PROMPT`` using the configured models."""
    log = logging.getLogger(__name__)

    registry = _build_registry()
    controller = ChatController(registry, editor_alias="editor")

    log.info("Sending prompt: %s", PROMPT)
    async for token in controller.astream_reply("demo", PROMPT):
        print(token, end="", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(demo())
    except KeyboardInterrupt:
        log.info("Aborted by user")
        exit(1)

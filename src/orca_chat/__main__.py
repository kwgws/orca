"""Simple interactive CLI for :mod:`orca_chat`."""

import asyncio
import logging
import os
from pathlib import Path

from orca_chat.config import LLMConfig, LLMRegistry
from orca_chat.controller import ChatController

handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
handler.setFormatter(formatter)

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(handler)


def _build_registry() -> LLMRegistry:
    registry = LLMRegistry()

    cfg = LLMConfig(
        model=os.environ.get("LLM", "default"),
        temperature=0.7,
        system=Path("./config/system_prompt.txt").read_text().strip(),
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


async def chat() -> None:
    """Run a simple REPL for interactive chatting."""

    registry = _build_registry()
    controller = ChatController(registry, editor_alias="editor")

    log.info("Starting CLI session")
    print("Type 'quit' or press Ctrl-D to exit.")

    session_id = "cli"

    while True:
        try:
            prompt = input("\u003e ").strip()
        except EOFError:
            print()
            break

        if not prompt or prompt.lower() in {"quit", "exit"}:
            break

        log.info("Sending prompt: %s", prompt)
        async for token in controller.astream_reply(session_id, prompt):
            print(token, end="", flush=True)
        print()


if __name__ == "__main__":
    try:
        asyncio.run(chat())
    except KeyboardInterrupt:
        log.info("Aborted by user")
        exit(1)

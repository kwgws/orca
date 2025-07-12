import asyncio
import logging
import os
from dataclasses import replace
from pathlib import Path

from ..orchestration import build_chat_graph
from ..session import ChatState
from .callbacks import (
    JSONWriterCallbackHandler,
    LogWriterCallbackHandler,
    StreamingWriterCallbackHandler,
)

_AI_COLOR = "\x1b[38;5;006m"
_RESET_COLOR = "\x1b[0m"
_LOG_FILE = Path("./logs/orca_chat.log")


def _setup_logging() -> None:
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(_LOG_FILE)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.info("Logging started: %s", _LOG_FILE)


def _clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _ai_writer(text: str, *, end="", flush=False) -> None:
    print(f"{_AI_COLOR}{text}{_RESET_COLOR}", end=end, flush=flush)


async def _async_repl() -> None:
    _clear_screen()
    _setup_logging()

    graph = build_chat_graph()
    callbacks = [
        LogWriterCallbackHandler(),
        JSONWriterCallbackHandler(),
        StreamingWriterCallbackHandler(
            writer=_ai_writer,
            silent_on_tags={"summarize_node"},
            stream_on_tags={"chat_node"},
        ),
    ]

    chat_state = ChatState()
    first_turn = True

    while True:
        try:
            if not first_turn:
                user_msg = input("> ").strip()
                if not user_msg:
                    continue
            else:
                user_msg = "Introduce yourself very briefly and get the ball rolling."
                first_turn = False
        except (EOFError, KeyboardInterrupt):
            print("Goodbye!\n")
            break
        print()

        chat_state = replace(chat_state, question=user_msg)
        result = await graph.ainvoke(chat_state, config={"callbacks": callbacks})
        chat_state = chat_state.merge(result)
        print()


def repl() -> None:
    asyncio.run(_async_repl())

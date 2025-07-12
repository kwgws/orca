import asyncio
import logging
from dataclasses import replace
from pathlib import Path

from ..orchestration import build_chat_graph
from ..session import ChatState
from .callbacks import (
    JSONWriterCallbackHandler,
    LogWriterCallbackHandler,
    StdoutWriterCallbackHandler,
)

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


async def repl() -> None:
    _setup_logging()

    graph = build_chat_graph()
    callbacks = [
        LogWriterCallbackHandler(),
        JSONWriterCallbackHandler(),
        StdoutWriterCallbackHandler(
            silent_on_tags={"summarize_node"}, stream_on_tags={"chat_node"}
        ),
    ]

    chat_state = ChatState()
    is_first_msg = True

    while True:
        try:
            if not is_first_msg:
                user_msg = (await asyncio.to_thread(input, "> ")).strip()
            else:
                user_msg = "Hello!"
                is_first_msg = False
            print()
        except (EOFError, KeyboardInterrupt):
            print("Goodbye!")
            break
        if not user_msg:
            continue

        chat_state = replace(chat_state, question=user_msg)
        result = await graph.ainvoke(
            chat_state,
            config={"callbacks": callbacks},
        )

        chat_state = chat_state.merge(result)
        print()

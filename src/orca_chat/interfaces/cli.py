import logging
from dataclasses import replace
from pathlib import Path

from ..orchestration import build_chat_graph
from ..session import ChatState
from .callbacks import JSONWriterCallbackHandler, LogWriterCallbackHandler

_LOG_FILE = Path("./logs/orca_chat.log")


def _setup_logging() -> None:
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(_LOG_FILE)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.info("Logging started: %s", _LOG_FILE)


async def repl() -> None:
    _setup_logging()
    graph = build_chat_graph()
    chat_state = ChatState()
    first_message = True

    while True:
        if first_message:
            first_message = False
            question = "Hello!"
        else:
            try:
                question = input("> ").strip()
                print()
            except (EOFError, KeyboardInterrupt):
                print("Goodbye!")
                break
            if not question:
                continue

        chat_state = replace(chat_state, question=question)
        result = await graph.ainvoke(
            chat_state,
            config={
                "callbacks": [
                    LogWriterCallbackHandler(),
                    JSONWriterCallbackHandler(),
                ]
            },
        )

        chat_state = chat_state.merge(result)
        print()

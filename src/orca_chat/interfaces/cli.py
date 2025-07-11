import logging
from pathlib import Path

from langchain_community.chat_message_histories import ChatMessageHistory

from ..orchestration import build_chat_graph
from ..session import ChatState
from .callbacks import JSONWriterCallbackHandler, LogWriterCallbackHandler

_LOG_FILE = Path("./logs/orca_chat.log")


def _setup_logging() -> None:
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(_LOG_FILE)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.info("Logging started: %s", _LOG_FILE)


async def repl() -> None:
    _setup_logging()

    chat_history = ChatMessageHistory()
    graph = build_chat_graph()

    print("CLI ready")
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("Goodbye!")
            break
        if not question:
            continue

        chat_history.add_user_message(question)
        result = await graph.ainvoke(
            ChatState(chat_history.messages),
            config={
                "callbacks": [
                    LogWriterCallbackHandler(),
                    JSONWriterCallbackHandler(),
                ]
            },
        )
        response = result["chat_history"][-1].content
        chat_history.add_ai_message(response)
        print(response)

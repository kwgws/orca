from langchain_core.chat_history import InMemoryChatMessageHistory


class SessionState:
    """Lightweight container for per-session state."""

    def __init__(self) -> None:
        self.history = InMemoryChatMessageHistory()
        self.precis = ""

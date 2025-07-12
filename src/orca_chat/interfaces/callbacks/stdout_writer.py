import random

from langchain.callbacks.base import AsyncCallbackHandler


def _thunk() -> str:
    return random.choice(
        [
            "Analyzing",
            "Brooding",
            "Considering",
            "Cogitating",
            "Deliberating",
            "Ideating",
            "Meditating",
            "Musing",
            "Mulling",
            "Pondering",
            "Reasoning",
            "Reckoning",
            "Reflecting",
            "Ruminating",
            "Thinking",
        ]
    )


class StdoutWriterCallbackHandler(AsyncCallbackHandler):
    """Callback handler that streams LLM tokens to stdout."""

    def __init__(
        self,
        *args,
        silent_on_tags: set[str] | None = None,
        stream_on_tags: set[str] | None = None,
    ):
        self._silent_on_tags = silent_on_tags or set()
        self._stream_on_tags = stream_on_tags or set()

    async def on_llm_start(self, *args, tags: list[str] | None = None, **kwargs) -> None:
        if not set(tags or []) & self._silent_on_tags:
            print(f"{_thunk()}...")

    async def on_llm_new_token(
        self, token: str, *args, tags: list[str] | None = None, **kwargs
    ) -> None:
        if (not set(tags or []) & self._silent_on_tags) and (
            set(tags or []) & self._stream_on_tags
        ):
            print(token, end="", flush=True)

    async def on_llm_end(self, *args, tags: list[str] | None = None, **kwargs) -> None:
        if (not set(tags or []) & self._silent_on_tags) and (
            set(tags or []) & self._stream_on_tags
        ):
            print()

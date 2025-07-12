import random
from collections.abc import Callable

from langchain.callbacks.base import AsyncCallbackHandler


def _thunk() -> str:
    return random.choice(
        [
            "Brooding",
            "Cogitating",
            "Deliberating",
            "Ideating",
            "Meditating",
            "Musing",
            "Pondering",
            "Reasoning",
            "Ruminating",
            "Thinking",
        ]
    )


class StreamingWriterCallbackHandler(AsyncCallbackHandler):
    """Streaming callback that writes tokens to stdout or a custom writer.

    Attributes
    ----------
    writer : callable, optional
        Function used to display tokens; defaults to :func:`print`.
    silent_on_tags : set of str, optional
        Tags that disable all output for a given invocation.
    stream_on_tags : set of str, optional
        Tags that enable token streaming output.
    """

    def __init__(
        self,
        *args,
        writer: Callable[..., None] | None = None,
        silent_on_tags: set[str] | None = None,
        stream_on_tags: set[str] | None = None,
    ):
        self._writer = writer or print
        self._silent_on_tags = silent_on_tags or set()
        self._stream_on_tags = stream_on_tags or set()

    async def on_llm_start(self, *args, tags: list[str] | None = None, **kwargs) -> None:
        if not set(tags or []) & self._silent_on_tags:
            self._writer(f"{_thunk()}...\n")

    async def on_llm_new_token(
        self, token: str, *args, tags: list[str] | None = None, **kwargs
    ) -> None:
        if (not set(tags or []) & self._silent_on_tags) and (
            set(tags or []) & self._stream_on_tags
        ):
            self._writer(token, end="", flush=True)

    async def on_llm_end(self, *args, tags: list[str] | None = None, **kwargs) -> None:
        if (not set(tags or []) & self._silent_on_tags) and (
            set(tags or []) & self._stream_on_tags
        ):
            self._writer("\n")

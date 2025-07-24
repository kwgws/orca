"""orca_chat/interfaces/callbacks/stdout_writer.py"""

from typing import Any

from langchain_core.callbacks.base import AsyncCallbackHandler
from langchain_core.outputs import LLMResult


class StdoutWriter(AsyncCallbackHandler):
    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        if tags and "out_silent" not in tags:
            print("Thinking...", flush=True)

    async def on_llm_new_token(
        self,
        token: str,
        *,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        if tags and "out_stream" in tags:
            print(token, end="", flush=True)

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        if tags and "out_stream" in tags:
            print()

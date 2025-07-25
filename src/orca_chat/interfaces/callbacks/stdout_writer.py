"""orca_chat/interfaces/callbacks/stdout_writer.py"""

from typing import Any

from langchain_core.callbacks.base import AsyncCallbackHandler
from langchain_core.outputs import LLMResult


class StdoutWriter(AsyncCallbackHandler):
    """Stream model output to the console."""

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Print a thinking message unless ``out_silent`` is present."""
        if tags and "out_silent" not in tags:
            tag = next((t for t in tags if t.startswith("node_")), "node_unknown")
            print(f"Entering node '{tag[5:]}' ...")

    async def on_llm_new_token(
        self,
        token: str,
        *,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Stream tokens when ``out_stream`` is enabled."""
        if tags and "out_stream" in tags:
            print(token, end="", flush=True)

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Finalize streaming output."""
        if tags and "out_stream" in tags:
            print()

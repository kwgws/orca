from typing import Any

from langchain_core.callbacks.base import AsyncCallbackHandler


class StdoutWriter(AsyncCallbackHandler):
    async def on_llm_new_token(
        self,
        token: str,
        *,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        if tags and "chat_node" in tags:
            print(token, end="", flush=True)

    async def on_llm_end(
        self,
        response: Any,
        *,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        if tags and "chat_node" in tags:
            print()

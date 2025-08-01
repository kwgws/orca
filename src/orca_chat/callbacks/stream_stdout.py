"""orca_chat/callbacks/stream_stdout.py"""

from typing import Any, override

from langchain_core.callbacks import BaseCallbackHandler


class StreamStdOut(BaseCallbackHandler):
    """Callback handler for streaming to the console."""

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> Any:
        """Run when LLM starts running."""
        print("## TO MODEL ##")
        for prompt in prompts:
            print(prompt)
        print("####\n")

    @override
    def on_llm_new_token(
        self,
        token: str,
        *args,
        tags: list[str] | None = None,
        **_,
    ) -> None:
        """Run on new LLM token."""
        if tags and "stream" in tags:
            print(token, end="", flush=True)

    def on_llm_end(
        self,
        *args: Any,
        tags: list[str] | None = None,
        **_,
    ) -> None:
        """Run when LLM ends running."""
        if tags and "stream" in tags:
            print()

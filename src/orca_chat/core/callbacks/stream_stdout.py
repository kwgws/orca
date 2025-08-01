from typing import Any, override

from langchain_core.callbacks import BaseCallbackHandler


class StreamStdOut(BaseCallbackHandler):
    """Callback handler for streaming to the console."""

    def on_llm_start(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Run when LLM starts running."""
        print("\nThinking...\n")

    @override
    def on_llm_new_token(
        self,
        token: str,
        **kwargs: Any,
    ) -> None:
        """Run on new LLM token."""
        print(token, end="", flush=True)

    def on_llm_end(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Run when LLM ends running."""
        print()

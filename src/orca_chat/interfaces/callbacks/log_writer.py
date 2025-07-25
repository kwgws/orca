"""orca_chat/interfaces/callbacks/log_writer.py"""

import logging
import re
from typing import Any

from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import LLMResult

log = logging.getLogger("orca_chat.llm")
_re_whitespace = re.compile(r"\s+")


class LogWriter(AsyncCallbackHandler):
    """Callback that logs prompts and responses using :mod:`logging`."""

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs,
    ) -> None:
        """Log each outgoing prompt."""
        for prompt in prompts:
            log_prompt = _re_whitespace.sub(" ", prompt).strip()
            if len(log_prompt) > 60:
                log_prompt = log_prompt[:60] + "..."
            log.info("To LLM: %s (%d chars)", log_prompt, len(prompt))

    async def on_llm_end(
        self,
        response: LLMResult,
        **kwargs,
    ) -> None:
        """Log each incoming response."""
        for gen in response.generations:
            reply = gen[0].text
            log_reply = _re_whitespace.sub(" ", reply).strip()
            if len(log_reply) > 60:
                log_reply = log_reply[:60] + "..."
            log.info("LLM replied: %s (%d chars)", log_reply, len(reply))

    async def on_llm_error(
        self,
        error: BaseException,
        **kwargs,
    ) -> None:
        """Log errors raised by the LLM itself."""
        log.error("LLM error: %s", error)

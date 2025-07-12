import logging
from typing import Any

import regex as re
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import LLMResult

log = logging.getLogger("orca_chat.llm")


class LogWriterCallbackHandler(AsyncCallbackHandler):
    """Callback that logs prompts and responses using :mod:`logging`."""

    async def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs) -> None:
        for i, prompt in enumerate(prompts):
            log_prompt = re.sub(r"\s+", " ", prompt).strip()
            if len(log_prompt) > 60:
                log_prompt = log_prompt[:60] + "..."
            log.info("LLM prompt %d: %s (%d chars)", i + 1, log_prompt, len(prompt))

    async def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        for i, gen in enumerate(response.generations):
            reply = gen[0].text
            log_reply = re.sub(r"\s+", " ", reply).strip()
            if len(log_reply) > 60:
                log_reply = log_reply[:60] + "..."
            log.info("LLM response %d: %s (%d chars)", i + 1, log_reply, len(reply))

    async def on_llm_error(self, error: BaseException, **kwargs) -> None:
        log.error("LLM error: %s", error)

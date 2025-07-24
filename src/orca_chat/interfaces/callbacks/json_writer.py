"""orca_chat/interfaces/callbacks/json_writer.py"""

import asyncio
import json
import os
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Any
from uuid import UUID

from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import LLMResult

from ...loaders import load_json

log = getLogger(__name__)


class JSONWriter(AsyncCallbackHandler):
    """Asynchronously write LLM prompts and responses to a JSON file."""

    def __init__(self, *, path: str | Path | None = None) -> None:
        if not path:
            log_path = os.getenv("LOG_FILE")
            if log_path:
                log_path = Path(log_path)
                self.file_path = log_path.with_stem("json")
            else:
                self.file_path = Path("./orca_chat.json")
        else:
            self.file_path = Path(path)

        self.file_lock = asyncio.Lock()
        self.buffer: list[str] = []

        super().__init__()

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        for prompt in prompts:
            await self._append_to_file(
                run_id=str(run_id),
                record={
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "prompt",
                    "text": prompt,
                    "tags": tags or [],
                },
            )

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        tags: list[str] | None = None,
        **kwargs,
    ) -> None:
        for gen in response.generations:
            reply = gen[0].text
            await self._append_to_file(
                run_id=str(run_id),
                record={
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "response",
                    "text": reply,
                    "tags": tags or [],
                },
            )

    async def _append_to_file(self, run_id: str, record: dict[str, Any]) -> None:
        """Serialize ``record`` to JSON, appending it to ``self.path``."""
        async with self.file_lock:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            data = load_json(self.file_path)
            if not data.get(run_id):
                data[run_id] = []
            data[run_id].append(record)

            self.file_path.write_text(json.dumps(data, indent=2))

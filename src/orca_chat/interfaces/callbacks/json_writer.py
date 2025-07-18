import asyncio
import json
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Any

import aiofiles
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import LLMResult

log = getLogger(__name__)


class JSONWriter(AsyncCallbackHandler):
    """Asynchronously write LLM prompts and responses to a JSON file."""

    def __init__(self, path="./logs/conversations.json"):
        self.path = Path(path)
        self.lock = asyncio.Lock()
        self.buffer = []

    async def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs):
        for prompt in prompts:
            await self._append_to_file(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "prompt",
                    "text": prompt,
                }
            )

    async def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        for gen in response.generations:
            reply = gen[0].text
            await self._append_to_file(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "response",
                    "text": reply,
                }
            )

    async def _append_to_file(self, record: dict[str, Any]) -> None:
        """Serialize ``record`` to JSON, appending it to ``self.path``."""
        async with self.lock:
            if not self.path.exists():
                self.path.parent.mkdir(parents=True, exist_ok=True)
                data = []
            else:
                async with aiofiles.open(self.path) as f:
                    try:
                        content = await f.read()
                        data = json.loads(content)
                    except json.JSONDecodeError as e:
                        log.error("Error parsing JSON from %s: %s", self.path, e)
                        data = []
            data.append(record)
            async with aiofiles.open(self.path, "w") as f:
                await f.write(json.dumps(data, indent=2))

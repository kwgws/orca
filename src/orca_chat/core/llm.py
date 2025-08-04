# orca_chat.core.llm

"""Central registry for Large-Language-Model (LLM) objects."""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from os import getenv
from typing import Any, Final, Self, cast

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

__all__: Final = ["LLM", "LLMStore"]
_SENTINEL: Final = object()

CacheKey = tuple[str, bool, str]

DEFAULT_URL = getenv("OPENAI_URL", "http://localhost:1234/v1")
DEFAULT_MODEL = getenv("OPENAI_MODEL", "llama3")
DEFAULT_USE_TOOLS = getenv("OPENAI_USE_TOOLS", "false")


@dataclass(slots=True, frozen=True)
class LLM:
    """Wrapper for LangChain chat model.

    Instances are frozen so they can be safely shared across asyncio tasks.

    Parameters
    ----------
    model
        The underlying LangChain model instance.
    supports_tools
        Whether the model can make structured tool calls.
    tools
        Tools bound to the model, if any.
    """

    model: Runnable
    tool_calling: bool = False
    tools: tuple[BaseTool, ...] | None = None

    @classmethod
    def from_env(
        cls,
        alias="default",
        *,
        callbacks: Sequence[BaseCallbackHandler] | None = None,
        tool_calling: bool | None = None,
        tools: Sequence[BaseTool] | None = None,
    ) -> Self:
        """Build a :class:`LLM` from the environment.

        Parameters are resolved in this order:
        1. ``<ALIAS>_URL`` / ``<ALIAS>_MODEL`` (most specific)
        2. ``OPENAI_URL``  / ``OPENAI_MODEL`` (project-wide default)
        3. Hard-coded URL ``"http://localhost:1234/v1"`` and model ``alias``
        """
        prefix = alias.upper()
        name = getenv(f"{prefix}_MODEL", DEFAULT_MODEL or alias)
        url = getenv(f"{prefix}_URL", DEFAULT_URL)

        model = ChatOpenAI(model=name, base_url=url)
        if callbacks:
            model = model.with_config(callbacks=callbacks)

        tool_calling = (
            getenv(f"{prefix}_USE_TOOLS", DEFAULT_USE_TOOLS).lower() in {"true", "yes"}
            if tool_calling is None
            else tool_calling
        )
        if tool_calling and tools:
            model = cast(BaseChatModel, model).bind_tools(tools)
            return cls(model=model, tool_calling=True, tools=tuple(tools))
        return cls(model=model, tool_calling=tool_calling)

    async def ainvoke(
        self, prompt: Sequence[BaseMessage], config: RunnableConfig | None = None
    ) -> BaseMessage:
        """Proxy for ``model.ainvoke()``."""
        return await self.model.ainvoke(prompt, config)

    async def with_config(self, **kwargs: Any) -> Self:
        """Proxy for ``model.with_config()``."""
        return replace(self, model=self.model.with_config(**kwargs))


@dataclass(slots=True, frozen=True)
class LLMStore:
    """Lightweight registry mapping string aliases to LLMs."""

    _store: dict[CacheKey, LLM] = field(default_factory=dict)
    _toolbox: dict[str, BaseTool] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get(
        self,
        alias: str | None,
        *,
        callbacks: Sequence[BaseCallbackHandler] | None = None,
        tool_calling: bool | object = _SENTINEL,
        tools: Sequence[BaseTool] | None = None,
    ) -> LLM:
        name = alias or "default"
        uses_tools = None if tool_calling is _SENTINEL else cast(bool | None, tool_calling)
        tools = tools or [t for t in self._toolbox.values()]
        cache_key: CacheKey = (name, bool(uses_tools), ",".join(t.name for t in tools))

        # Cached?
        if (llm := self._store.get(cache_key)) is not None:
            return llm
        async with self._lock:
            if (llm := self._store.get(cache_key)) is not None:
                return llm

        # Not cached -- (re)build.
        llm = LLM.from_env(name, callbacks=callbacks, tool_calling=uses_tools, tools=tools)
        async with self._lock:
            self._store[cache_key] = llm
        return llm

    async def add_tools(self, *tools: BaseTool) -> None:
        async with self._lock:
            self._toolbox.update({t.name: t for t in tools})

    async def remove_tools(self, *tools: BaseTool) -> None:
        async with self._lock:
            [self._toolbox.pop(t.name, None) for t in tools]

    async def clear_tools(self) -> None:
        async with self._lock:
            self._toolbox.clear()

# orca_chat/llm.py

"""LLM utilities for managing LangChain-compatible chat models."""

import asyncio
from collections.abc import Callable, Coroutine, Hashable, Sequence
from os import getenv
from typing import Any, Final, cast

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

__all__: Final = ["clear_cache", "get_llm"]

_MODEL_CACHE: dict[tuple[Hashable, ...], ChatOpenAI] = {}
_INFLIGHT: dict[tuple[Hashable, ...], asyncio.Task[ChatOpenAI]] = {}
_CACHE_LOCK = asyncio.Lock()


# -----------------------------------------------------------------------------
# Default Client Settings
# -----------------------------------------------------------------------------

DEFAULT_URL = getenv("OPENAI_URL", "http://localhost:1234/v1")
DEFAULT_MODEL = getenv("OPENAI_MODEL", "default")


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


async def get_llm(
    *,
    model: str | None = None,
    base_url: str | None = None,
    tools: Sequence[BaseTool] | None = None,
    streaming: bool = True,
    callbacks: Sequence[BaseCallbackHandler] | None = None,
    **kwargs,
) -> ChatOpenAI:
    """Retrieve or create a cached LangChain-compatible chat model bound with
    optional tools.

    Parameters
    ----------
    model : str, optional
        Identifier for the LLM, defaults to environment variable
        ``OPENAI_MODEL`` or to ``"default"``.
    base_url : str, optional
        Endpoint URL of the backend API, defaults to environment variable
        ``OPENAI_URL`` or to ``"http://localhost:1234/v1"``.
    tools : Sequence[BaseTool], optional
        A sequence of LangChain tools to bind to the model. Duplicate tool
        names are not permitted.
    streaming : bool, default=True
        If True, the model will stream responses asynchronously.
    callbacks : Sequence[BaseCallbackHandler], optional
        Callback handlers to pass to LangChain for tracing or logging.
    **kwargs
        Additional keyword arguments directly passed to :class:`ChatOpenAI`.

    Returns
    -------
    ChatOpenAI
        An instance of a LangChain-compatible chat model, optionally configured
        with streaming, callbacks, and tools.

    Raises
    ------
    ValueError
        If duplicate tool names are detected.
    """
    model = model or DEFAULT_MODEL
    base_url = base_url or DEFAULT_URL
    key = _get_key(model, base_url, streaming, kwargs)

    async def _factory():
        return ChatOpenAI(
            model=model, base_url=base_url, streaming=streaming, **kwargs
        )

    llm = await _get_llm(key, _factory)

    if tools:
        tb = set()
        dupes = [t.name for t in tools if t.name in tb or tb.add(t.name)]
        if dupes:
            raise ValueError(f"Duplicate tool name(s): {dupes}")
        llm = cast(ChatOpenAI, llm.bind_tools(tools))

    if callbacks:
        llm = cast(ChatOpenAI, llm.with_config(callbacks=callbacks))

    return llm


def clear_cache() -> None:
    """Clear the internal LLM model cache."""
    _MODEL_CACHE.clear()
    _INFLIGHT.clear()


# -----------------------------------------------------------------------------
# Internal Helpers
# -----------------------------------------------------------------------------


async def _get_llm(
    key: tuple[Hashable, ...],
    factory: Callable[[], Coroutine[Any, Any, ChatOpenAI]],
) -> ChatOpenAI:
    """Retrieve a cached LLM instance or create and cache one using the
    provided factory.

    Parameters
    ----------
    key : tuple[Hashable, ...]
        A unique key identifying the LLM configuration.
    factory : callable
        Async function that returns a configured ChatOpenAI instance.

    Returns
    -------
    ChatOpenAI
        Cached or newly built LLM instance.
    """
    if llm := _MODEL_CACHE.get(key):
        return llm

    async with _CACHE_LOCK:
        if (llm := _MODEL_CACHE.get(key)) is not None:
            return llm
        task = _INFLIGHT.get(key)
        if task is None:
            task = asyncio.create_task(factory())
            _INFLIGHT[key] = task

    try:
        llm = await task
        async with _CACHE_LOCK:
            _MODEL_CACHE[key] = llm
        return llm

    finally:
        async with _CACHE_LOCK:
            if _INFLIGHT.get(key) is task:
                _INFLIGHT.pop(key, None)


def _get_key(
    model: str,
    base_url: str,
    streaming: bool,
    kwargs: dict[str, Any],
) -> tuple[Hashable, ...]:
    """Generate a unique, hashable key representing LLM configuration.

    Parameters
    ----------
    model : str
        Model identifier.
    base_url : str
        Backend URL.
    streaming : bool
        Whether responses are streamed.
    kwargs : dict[str, Any]
        Additional keyword arguments.

    Returns
    -------
    tuple[Hashable, ...]
        An immutable tuple suitable for use as a cache key.

    Notes
    -----
    Non-hashable extra kwargs are converted to their string representations
    using `repr`.
    """
    extra = tuple(sorted((k, repr(v)) for k, v in kwargs.items()))
    return (model, base_url, streaming, extra)

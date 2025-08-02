"""orca_chat.core.llm
Central registry for Large-Language-Model (LLM) objects.

`LLMStore` lets skills ask for a model by alias and forget the rest.
On first access the store will:

1. Look for a factory/instance already registered under that alias.
2. Otherwise, create and register a streaming `ChatOpenAI` using
   environment variables of the form ``<ALIAS>_URL`` / ``<ALIAS>_MODEL``
   (falling back to the global ``OPENAI_URL`` / ``OPENAI_MODEL`` and,
   finally, to sensible defaults).

Results from user-supplied factories are cached by ``(factory, callbacks)``
so multiple skills can share the same connection without rebuilding it.
"""

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from os import getenv
from typing import Final, cast

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

__all__: Final = ["LLMStore"]

Callbacks = Sequence[BaseCallbackHandler] | None
LLMFactory = Callable[[Callbacks], BaseChatModel]
CacheKey = tuple[LLMFactory, tuple[BaseCallbackHandler, ...]]

DEFAULT_URL: Final = getenv("OPENAI_URL", "http://localhost:1234/v1")
DEFAULT_MODEL: Final = getenv("OPENAI_MODEL", "")


@dataclass(slots=True)
class LLMStore:
    """Lightweight registry mapping string aliases to LLMs.

    Entries can be either:
    - Instances: ready-to-use ``BaseChatModel`` subclass.
    - Factories: ``callable(callbacks) -> BaseChatModel`` that returns a fresh
      instance each time it is invoked.
    """

    _store: dict[str, LLMFactory] = field(default_factory=dict)
    _cache: dict[CacheKey, BaseChatModel] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get(
        self, alias: str | None, callbacks: Callbacks = None, *, use_cache=True
    ) -> BaseChatModel:
        """Return an LLM for ``alias``, cloning or instantiating as needed.

        Parameters
        ----------
        alias:
            Symbolic name for the model. ``None`` resolves to the literal
            ``"default"`` alias.
        callbacks:
            Optional sequence of LangChain callback handlers to inject via
            ``with_config`` (for instances) or to pass into a factory call.
        use_cache:
            When ``True`` (default) results are cached so identical
            `(factory, callbacks)` pairs share a single model instance.

        Returns
        -------
        BaseChatModel
            The requested LLM, configured with the provided callbacks.

        Raises
        ------
        ValueError
            If the alias is unknown and automatic registration fails (should
            only occur in exotic misconfigurations).
        """
        name = alias or "default"
        factory = self._store.get(name)

        if factory is None:  # Not found; lock and check again.
            async with self._lock:
                factory = self._store.get(name)

        if factory is None:  # Still not found; create a new factory.
            async with self._lock:
                if name != "default" and "default" in self._store:
                    factory = self._store["default"]
                else:
                    instance = _default_llm_instance(name)
                    factory = _wrap_as_factory(instance)
                self._store[name] = factory

        if not use_cache:  # If we're not using the cache we can stop here.
            return factory(callbacks)

        # Otherwise, we repeat the pattern: check first...
        key: CacheKey = (factory, tuple(callbacks) if callbacks else ())
        model = self._cache.get(key)
        if model:
            return model

        # ...then lock and recheck.
        built = factory(callbacks)
        async with self._lock:
            return self._cache.setdefault(key, built)


def _wrap_as_factory(obj: LLMFactory | BaseChatModel) -> LLMFactory:
    """Return a factory if we got an instance."""
    if isinstance(obj, BaseChatModel):
        model = obj

        def _factory(callbacks: Callbacks) -> BaseChatModel:
            return cast(BaseChatModel, model.with_config(callbacks=callbacks))

        return _factory

    return cast(LLMFactory, obj)


def _default_llm_instance(alias: str) -> BaseChatModel:
    """Create a streaming ``ChatOpenAI`` for ``alias`` using environment vars.

    This is only invoked when an alias is first requested and has never been
    manually registered, effectively making lazy registration the default.

    Notes
    -----
    Parameters are resolved in this order:
    1. ``<ALIAS>_URL`` / ``<ALIAS>_MODEL`` (most specific)
    2. ``OPENAI_URL``  / ``OPENAI_MODEL`` (project-wide default)
    3. Hard-coded URL ``"http://localhost:1234/v1"`` and model ``alias``
    """
    prefix = alias.upper()
    url = getenv(f"{prefix}_URL", DEFAULT_URL)
    model = getenv(f"{prefix}_MODEL", DEFAULT_MODEL or alias)
    return ChatOpenAI(base_url=url, model=model, streaming=True)

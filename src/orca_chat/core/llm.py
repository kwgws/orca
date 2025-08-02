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

    _store: dict[str, LLMFactory | BaseChatModel] = field(default_factory=dict)
    _cache: dict[CacheKey, BaseChatModel] = field(default_factory=dict)

    def get(
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
            When ``True`` (default) and the alias maps to a *factory*,
            results are cached so identical `(factory, callbacks)` pairs
            share a single model instance.

        Returns
        -------
        BaseChatModel
            The requested LLM, configured with the provided callbacks.

        Raises
        ------
        ValueError
            If the alias is unknown and automatic registration fails (should
            only occur in exotic env-var misconfigurations).
        """

        target = alias or "default"
        try:
            llm = self._store[target]
        except KeyError:
            # Fallback to "default" if present; else lazily register alias.
            if target != "default" and "default" in self._store:
                llm = self._store["default"]
            else:
                llm = _default_llm_factory(target)
                self._store[target] = llm

        # Are we working with an instantiated LLM?
        if isinstance(llm, BaseChatModel):
            return cast(BaseChatModel, llm.with_config(callbacks=callbacks))

        # ...or a factory?
        factory = cast(LLMFactory, llm)
        if not use_cache:
            return factory(callbacks)

        key: CacheKey = (factory, tuple(callbacks) if callbacks else ())
        if key not in self._cache:
            self._cache[key] = factory(callbacks)
        return self._cache[key]


def _default_llm_factory(alias: str) -> BaseChatModel:
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

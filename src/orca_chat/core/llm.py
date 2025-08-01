"""orca_chat/core/llm.py"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Final, cast

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel

__all__: Final = ["LLMStore"]

CacheKey = tuple[int, int]  # (id(factory), id(callbacks_tuple))
Callbacks = Sequence[BaseCallbackHandler] | None
LLMFactory = Callable[[Callbacks], BaseChatModel]


@dataclass(slots=True)
class LLMStore:
    """Registry mapping *aliases* to LLM factories/instances."""

    _store: dict[str, LLMFactory | BaseChatModel] = field(default_factory=dict)
    _cache: dict[CacheKey, BaseChatModel] = field(default_factory=dict)

    def register(self, alias: str, obj: LLMFactory | BaseChatModel) -> None:
        """Register *alias* to a model *instance* or a *factory*.

        The alias should be a stable, human-readable string. Factories must
        accept an optional sequence of callbacks and return a fresh
        :class:`ChatOpenAI` each call.
        """

        if alias in self._store:
            raise ValueError(f"Alias already registered: {alias!r}")
        self._store[alias] = obj

    def get(
        self, alias: str | None, callbacks: Callbacks = None, *, use_cache=True
    ) -> BaseChatModel:
        """Return an LLM bound to *alias*.

        If the registered entry is a **factory**, we invoke it (optionally with
        *callbacks*) and optionally cache the result. if it is already an
        **instance** we clone it via ``with_config`` to inject callbacks.
        """

        # Are we working with an instantiated LLM?
        target = alias or "default"
        try:
            llm = self._store[target]
        except KeyError as e:
            if target != "default" and "default" in self._store:
                llm = self._store["default"]
            else:
                raise ValueError(f"Unknown LLM alias: {alias!r}") from e

        if isinstance(llm, BaseChatModel):
            return cast(BaseChatModel, llm.with_config(callbacks=callbacks))

        # ...or a factory?
        factory = cast(LLMFactory, llm)
        if not use_cache:
            return factory(callbacks)

        key: CacheKey = (id(factory), id(tuple(callbacks) if callbacks else ()))
        if key not in self._cache:
            self._cache[key] = factory(callbacks)
        return self._cache[key]

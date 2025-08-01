"""orca_chat/core/message.py"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from typing import cast

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel

__all__ = ["LLMStore"]

LLMFactory = Callable[[Sequence[BaseCallbackHandler] | None], BaseChatModel]


@dataclass(slots=True)
class LLMStore:
    """Registry mapping *aliases* to LLM factories/instances."""

    _store: dict[str, LLMFactory | BaseChatModel] = field(default_factory=dict)

    def register(
        self,
        alias: str,
        obj: LLMFactory | BaseChatModel,
    ) -> None:
        """Register *alias* to a model *instance* or a *factory*.

        The alias should be a stable, human-readable string. Factories must
        accept an optional sequence of callbacks and return a fresh
        :class:`ChatOpenAI` each call.
        """

        if alias in self._store:
            raise ValueError(f"Alias already registered: {alias!r}")
        self._store[alias] = obj

    def get(
        self,
        alias: str,
        callbacks: Sequence[BaseCallbackHandler] | None = None,
        *,
        use_cache=True,
    ) -> BaseChatModel:
        """Return an LLM bound to *alias*.

        If the registered entry is a **factory**, we invoke it (optionally with
        *callbacks*) and optionally cache the result. if it is already an
        **instance** we clone it via ``with_config`` to inject callbacks.
        """

        # Are we working with an instantiated LLM?
        try:
            llm = self._store[alias]
        except KeyError as e:
            raise ValueError(f"Unknown LLM alias: {alias!r}") from e
        if isinstance(llm, BaseChatModel):
            return cast(BaseChatModel, llm.with_config(callbacks=callbacks))

        # ...or a factory?
        factory = llm
        if not use_cache:
            return factory(callbacks)

        @lru_cache(maxsize=1)
        def _cached(cb_key: int | None) -> BaseChatModel:
            # We can't directly cache on the callbacks list (unhashable),
            # so we use ``id(callbacks)`` instead.  Different callbacks
            # return different cache entries.
            callback_seq = callbacks
            return factory(callback_seq)

        return _cached(id(tuple(callbacks)) if callbacks else 0)

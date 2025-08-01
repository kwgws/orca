"""orca_chat/core/node.py"""

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Self, TypeVar, cast

__all__ = ["Node", "NodeStore"]

T = TypeVar("T")


@dataclass(slots=True, frozen=True)
class Node[T]:
    """A registry entry describing *how* to produce a resource.

    The factory may be sync or async. Calling the Node returns the produced
    instance.
    """

    name: str
    factory: Callable[..., Awaitable[T]]
    tags: frozenset[str] = field(default_factory=frozenset)
    llm_alias: str | None = None

    async def __call__(self, *args: Any, **kwargs: Any) -> T:
        return await self.factory(*args, **kwargs)


@dataclass(slots=True)
class NodeStore:
    """Async-safe registry for :class:`Node` objects."""

    _store: dict[str, Node[Any]] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def register(
        self,
        name: str,
        factory: Callable[..., Any],
        *,
        tags: set[str] | None = None,
        llm_alias: str | None = None,
        **kwargs: Any,
    ) -> Node:
        """Add a node to the store."""
        node = Node(
            name=name,
            factory=_make_async(factory),
            tags=frozenset(tags or ()),
            llm_alias=llm_alias,
            **kwargs,
        )

        async with self._lock:
            if name in self._store:
                raise KeyError(f"Node {name!r} already exists")
            self._store[name] = node

        return node

    async def get(self, name: str) -> Node[Any]:
        """Return the :class:`Node` registered under *name*."""
        async with self._lock:
            try:
                return self._store[name]
            except KeyError:
                raise ValueError(f"Node not found: {name!r}") from None

    async def get_factory(self, name: str) -> Callable[..., Awaitable[Any]]:
        """Return the factory callable registered under name."""
        async with self._lock:
            try:
                return self._store[name].factory
            except KeyError:
                raise ValueError(f"Node not found: {name!r}") from None

    async def all(self, *, filter_tags: set[str] | None = None) -> list[str]:
        """Return sorted list of node names, filtered by *filter_tags*."""
        async with self._lock:
            return sorted(
                name
                for name, node in self._store.items()
                if not filter_tags or filter_tags <= node.tags
            )

    async def remove(self, name: str) -> None:
        """Delete node *name* from the store (noop if absent)."""
        async with self._lock:
            self._store.pop(name, None)

    async def clear(self) -> None:
        """Remove **all** nodes."""
        async with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    async def __aiter__(self) -> AsyncGenerator[str]:
        async with self._lock:
            names = sorted(self._store.keys())
        for name in names:
            yield name

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.clear()


def _make_async[T](factory: Callable[..., T | Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Normalize *factory* so the result is always awaitable."""

    async def _call(*args: Any, **kwargs: Any) -> T:
        value = factory(*args, **kwargs)
        if asyncio.iscoroutine(value):
            return await value
        return cast(T, value)

    return _call

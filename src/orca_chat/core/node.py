"""orca_chat.core.node
Light-weight registry for  anything that can be invoked by the state graph.

A :class:`Node` is a factory that can create an LLM-driven skill, call a
microservice, read a database, whatever.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Final, ParamSpec, TypeVar, cast

__all__: Final = ["Node", "NodeStore"]

T = TypeVar("T")
P = ParamSpec("P")


@dataclass(slots=True, frozen=True)
class Node[T]:
    """A registry entry describing how to create a graph component.

    Parameters
    ----------
    name:
        Registry key used by :class:`NodeStore`.
    factory:
        Callable that turns `(*args, **kwargs)` into an awaitable result of
        type ``T``. Synchronous functions are automatically wrapped into a
        coroutine by :func:`_make_async`.
    tags:
        Immutable set of strings for tracing / metrics.
    metadata:
        Scratch data for graph.
    """

    name: str
    factory: Callable[..., Awaitable[T]]
    tags: frozenset[str] = field(default_factory=frozenset)
    metadata: dict[str, Any] = field(default_factory=dict)

    async def __call__(self, *args: Any, **kwargs: Any) -> T:
        """Delegate to :pyattr:`factory`, always returning awaitable `T`."""
        return await self.factory(*args, **kwargs)


@dataclass(slots=True)
class NodeStore:
    """Async-safe registry for :class:`Node` objects."""

    _store: dict[str, Node[Any]] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def register(
        self,
        name: str,
        factory: Callable[P, T] | Callable[P, Awaitable[T]],
        *,
        tags: set[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Node[T]:
        """Atomically add a new node and return it.

        Raises
        ------
        KeyError
            If ``name`` is already registered.
        """

        async with self._lock:
            if name in self._store:
                raise KeyError(f"Node already exists: {name!r}")

            node = Node[T](
                name=name,
                factory=_make_async(factory),
                tags=frozenset(tags or {}),
                metadata=metadata or {},
            )
            self._store[name] = cast(Node[Any], node)
            return node

    async def get(self, name: str) -> Node[Any]:
        """Return the :class:`Node` registered under ``name``.

        Raises
        ------
        ValueError
            If ``name`` is unknown.
        """
        async with self._lock:
            try:
                return self._store[name]
            except KeyError:
                raise KeyError(f"Node not found: {name!r}") from None

    async def get_factory(self, name: str) -> Callable[..., Awaitable[Any]]:
        """Return the factory callable registered under ``name``."""
        return (await self.get(name)).factory

    async def all(self, *, filter_tags: set[str] | None = None) -> list[str]:
        """Return sorted list of node names, filtered by ``filter_tags``."""
        async with self._lock:
            return sorted(
                name
                for name, node in self._store.items()
                if not filter_tags or filter_tags <= node.tags
            )

    async def remove(self, name: str) -> None:
        """Delete node ``name`` from the store, ignore if absent."""
        async with self._lock:
            self._store.pop(name, None)

    async def clear(self) -> None:
        """Remove all nodes."""
        async with self._lock:
            self._store.clear()


def _make_async(
    factory: Callable[P, T] | Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[T]]:
    """Ensure ``factory`` is awaitable regardless of its original form.

    If ``factory`` is already an async def, it is returned unchanged so that
    LangChain can inject metadata to ``config``.

    Otherwise we wrap the call and ``await`` the result if it is a coroutine,
    This lets callers write synchronous factories without caring about the
    event-loop context.
    """

    if asyncio.iscoroutinefunction(factory):
        return cast("Callable[P, Awaitable[T]]", factory)

    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        result = factory(*args, **kwargs)
        return await result if asyncio.iscoroutine(result) else cast(T, result)

    return _wrapper

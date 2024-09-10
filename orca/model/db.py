"""
Database tools for asynchronous session handling.

This module provides utilities for managing asynchronous database sessions
using SQLAlchemy's `AsyncSession`. It includes functions for initializing the
database engine, managing transactional scopes, and handling errors with retry
logic. The goal is to simplify and robustly handle common database operations
in an asynchronous environment, ensuring consistency and ease of use across the
application.
"""

import asyncio
import functools
import logging
from contextlib import asynccontextmanager
from functools import wraps
from random import random
from typing import Any, AsyncGenerator, Callable, Coroutine

import sqlalchemy.exc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from orca import config

log = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
"""Global instance of the database engine."""

_AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None
"""Global instance of the asynchronous session factory."""

db_lock = asyncio.Lock()
"""Global `asyncio.Lock` instance used to synchronize access to critical
database operations.

Example:
    >>> from model.db import db_lock
    >>> async def critical_task():
    >>>     async with db_lock:
    >>>         pass
"""

file_semaphore = asyncio.Semaphore(config.open_file_limit)

TRANS_EXC = (
    sqlalchemy.exc.InterfaceError,
    sqlalchemy.exc.InternalError,
    sqlalchemy.exc.OperationalError,
    sqlalchemy.exc.TimeoutError,
    asyncio.TimeoutError,
)
"""Transient exceptions

Transient exceptions (like `OperationalError`, `TimeoutError`, etc.) are errors
that are usually temporary, caused by issues like network glitches or brief
database unavailability.
"""


def handle_sql_errors(
    func: Callable[..., Coroutine[Any, Any, Any]]
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Handles SQL exceptions and retries transient exceptions at intervals
    with exponential backoff.

    This decorator is designed to wrap asynchronous database functions. It
    specifically handles transient SQL exceptions by retrying the operation a
    configurable number of times, using exponential backoff with jitter to
    avoid collision. If the retries are exhausted, the operation fails with a
    `RuntimeError`.

    In addition to transient exceptions, it also catches all `SQLAlchemyError`
    exceptions, logging the error and re-raising it as a `RuntimeError`.

    Notes:
    - The retry logic is configurable via `config.db.retries`. Ensure that
      the configuration is properly set.
    - Transient exceptions (e.g., `OperationalError`) are automatically
      retried. Non-transient SQL errors will raise a `RuntimeError`.
    - The exponential backoff uses the formula `attempt**2 + random()` to
      determine the sleep time before the next retry.

    Args:
        func ((...) -> Coroutine[Any, Any, Any]]): Asynchronous database function.

    Returns:
        Wrapped asynchronous function with error handling and retry logic.

    Raises:
        RuntimeError: Raised when the database operation fails after
            exhausting all retries or encounters an unrecoverable exception.

    Example:
        >>> @handle_sql_errors
        >>> async def execute_query(session, query):
        >>>    return await session.execute(query)
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        for attempt in range(1, config.db.retries + 2):
            try:
                return await func(*args, **kwargs)

            except TRANS_EXC as e:
                if "unable to open database file" in str(e):
                    raise e

                elif attempt <= config.db.retries:
                    sleep_time = attempt**2 + random()  # jitter vs collision
                    log.warning(
                        "🚧 Transient error in database operation '%s', "
                        "retrying in %.2f seconds (attempt %d of %d)",
                        func.__name__,
                        sleep_time,
                        attempt,
                        config.db.retries,
                    )
                    await asyncio.sleep(sleep_time)
                else:
                    log.exception(
                        "💣 Fatal error in database operation '%s' after %d attempts",
                        func.__name__,
                        attempt,
                    )
                    raise e

            except SQLAlchemyError:
                log.exception(
                    "💣 Fatal error in database operation '%s'",
                    func.__name__,
                )
                raise

    return wrapper


@handle_sql_errors
async def init_async_engine(uri: str | None = None) -> None:
    """Initializes the global asynchronous database engine and session factory.

    Sets up the global database engine and session factory using the provided
    URI. If no URI is specified, the function defaults to the global
    application configuration.

    Args:
        uri (str, optional): Database URI. Defaults to the application's
            database URI configuration if `None`.
    """
    global _engine, _AsyncSessionLocal
    async with db_lock:
        if _engine or _AsyncSessionLocal:
            return
        log.debug("🧬 Initializing database engine at %s", uri or config.db.uri)
        _engine = create_async_engine(uri or config.db.uri)
        _AsyncSessionLocal = async_sessionmaker(bind=_engine, expire_on_commit=False)


def get_async_engine() -> AsyncEngine:
    """Retrieves the global asynchronous database engine.

    This function returns the initialized global asynchronous database engine.
    It raises a `ValueError` if the engine has not been initialized.

    Returns:
        Initialized global asynchronous database engine.

    Raises:
        ValueError: Engine has not been initialized.
    """
    global _engine
    if not _engine:
        raise ValueError("Cannot access database engine before it has been initialized")
    return _engine


async def teardown_async_engine() -> None:
    global _engine
    if not _engine:
        raise ValueError("Cannot tear down engine before it has been initialized")
    await _engine.dispose()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, Any]:
    """Provides an asynchronous transactional scope around database operations.

    This context manager yields an `AsyncSession` for performing database
    operations within a transactional scope.

    Yields:
        An asynchronous database session.

    Raises:
        ValueError: Session factory has not been initialized.
    """
    global _AsyncSessionLocal
    if not _AsyncSessionLocal:
        raise ValueError(
            "Cannot create database session before engine has been initialized"
        )
    session = _AsyncSessionLocal()
    try:
        log.debug("🧬 Creating new database session")
        yield session
    finally:
        await session.close()


def with_async_session(
    func: Callable[..., Coroutine[Any, Any, Any]]
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Provides session management and SQL error handling for asynchronous
    database operations.

    This decorator ensures that an `AsyncSession` is available to the decorated
    function and applies retry logic for transient SQL exceptions. It will
    handle sessions and retries automatically so the decorated function can
    focus on business logic.

    Args:
        func ((...) -> Coroutine[Any, Any, Any]]): Coroutine to be decorated.

    Returns:
        Decorated coroutine with session management and error handling.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        session = kwargs.get("session")
        if not isinstance(session, AsyncSession):
            async with get_async_session() as session:
                kwargs["session"] = session
                return await func(*args, **kwargs)
        return await func(*args, **kwargs)

    return handle_sql_errors(wrapper)


@handle_sql_errors
async def save(
    obj: DeclarativeBase, *, immediate: bool = True, session: AsyncSession
) -> None:
    """Save an object to the database within the current session.

    This function attempts to save an object to the database. If `immediate` is
    `True`, the session is committed immediately after adding the object.

    Args:
        obj (DeclarativeBase): Object to save.
        session (AsyncSession): Active database session.
        immediate (bool, optional): If `True`, commits the session immediately
            after saving the object. Defaults to `False`.
    """
    try:
        log.debug("💾 Adding to database session %s", type(obj).__name__)
        session.add(obj)
        if immediate:
            async with db_lock:
                log.debug("⏩ Committing database session")
                await session.commit()

    except TRANS_EXC:
        if session.in_transaction() or session.in_nested_transaction():
            async with db_lock:
                log.warning("⏪ Rolling back database session")
                await session.rollback()
        raise

"""
Base SQLAlchemy mixins. All classes in the model need to inherit from `Base`.

This module provides foundational classes for SQLAlchemy models, offering
common attributes and methods for CRUD operations, status tracking, and
serialization. By inheriting from these mixins, models gain essential
functionalities that streamline database interactions, reduce redundancy, and
ensure consistent behavior across the application.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any, Self

from sqlalchemy import String, desc, func, select
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    declared_attr,
    mapped_column,
)

from orca.helpers import create_checksum, create_guid, dt_now, serialize
from orca.model.db import save, with_async_session

log = logging.getLogger(__name__)


class Base(AsyncAttrs, MappedAsDataclass, DeclarativeBase):
    """Base model class, provides common table properties and CRUD methods.

    This class should be inherited by all SQLAlchemy models in the application.
    It includes fundamental attributes such as a globally unique identifier
    (GUID), and timestamps for creation and last update. Additionally, it
    offers a suite of methods for basic CRUD (Create, Read, Update, Delete)
    operations, ensuring that each model has a consistent interface for
    interacting with the database.

    Attributes:
        guid (str): Stable, URL-safe, 22-character unique identifier.
        created_at (datetime): When the object was created (UTC).
        updated_at (datetime): When the object was last updated (UTC).
    """

    __abstract__ = True  # only to be used as a mixin
    guid: Mapped[str] = mapped_column(
        String(22), init=False, primary_key=True, default_factory=create_guid
    )
    created_at: Mapped[datetime] = mapped_column(init=False, insert_default=dt_now())
    updated_at: Mapped[datetime] = mapped_column(
        init=False, insert_default=dt_now(), onupdate=dt_now()
    )
    tags: Mapped[str] = mapped_column(String(255), init=False, insert_default="")
    comment: Mapped[str] = mapped_column(init=False, insert_default="")

    @declared_attr  # type: ignore (SQLAlchemy handles conversion)
    def __tablename__(cls) -> str:
        """Generates table name based on class name."""
        name = cls.__name__.lower()
        return f"{name}{'es' if name.endswith('s') or name.endswith('ch') else 's'}"

    @classmethod
    @with_async_session
    async def get(cls, guid: str, *, session: AsyncSession) -> Self | None:
        """Retrieves an object from the database by its GUID.

        Args:
            guid (str): The object's GUID.
            session (AsyncSession, optional): An active asynchronous database
                session. If not provided, the method will create and manage its
                own session.

        Returns:
            Reference to the object, or `None` if not found.
        """
        log.debug("🔍 Getting %s <%s>", cls.__name__, guid)
        return await session.get(cls, guid)

    @classmethod
    @with_async_session
    async def get_all(cls, *, session: AsyncSession) -> list[Self]:
        """Retrieves all instances of an object from the database.

        Args:
            session (AsyncSession, optional): An active asynchronous database
                session. If not provided, the method will create and manage its
                own session.

        Returns:
            List of all objects found. If none, will return an empty list.
        """
        log.debug("🔍 Getting all %s", cls.__tablename__)
        result = await session.execute(select(cls))
        return [obj for obj in result.scalars().all()]

    @classmethod
    @with_async_session
    async def get_latest(cls, *, session: AsyncSession) -> Self | None:
        """Retrieves the most recent instance from the database.

        This method queries the database for the latest entry based on the
        creation timestamp and returns it. If no entries are found, it
        returns `None`.

        Args:
            session (AsyncSession, optional): An active asynchronous database
                session. If not provided, the method will create and manage its
                own session.

        Returns:
            The most recent instance, or `None` if none exist.
        """
        log.debug("🔍 Getting latest %s", cls.__name__)
        return (
            (await session.execute(select(cls).order_by(desc(cls.created_at))))
            .scalars()
            .first()
        )

    @classmethod
    @with_async_session
    async def get_total(cls, *, session: AsyncSession) -> int:
        """Counts total instances of this object in the database.

        Args:
            session (AsyncSession, optional): An active asynchronous database
                session. If not provided, the method will create and manage its
                own session.

        Returns:
            Count of all instances of this object in the database.
        """
        log.debug("🔍 Getting total number of %s", cls.__tablename__)
        result = await session.execute(select(func.count()).select_from(cls))
        return result.scalar() or 0

    @classmethod
    @with_async_session
    async def create(
        cls, *args, immediate: bool = True, session: AsyncSession, **kwargs
    ) -> Self:
        """Creates and persists a new instance of this object.

        Args:
            *args: Positional arguments to be passed to the object's default
                constructor.
            immediate (bool, optional): If `True`, commits the session
                immediately after saving the object. Defaults to `True`.
            session (AsyncSession, optional): An active asynchronous database
                session. If not provided, the method will create and manage its
                own session.
            **kwargs: Keyword arguments to be passed to the object's default
                constructor.

        Returns:
            New instance of this object, now saved to the database.
        """
        log.debug("✨ Creating new %s", cls.__name__)
        obj = cls(*args, **kwargs)
        await save(obj, immediate=immediate, session=session)
        return obj

    @with_async_session
    async def update(
        self, data: dict[str, Any], *, immediate: bool = True, session: AsyncSession
    ) -> None:
        """Updates the current instance with provided dictionary.

        Args:
            data (dict[str, Any]): Dictionary containing column values to update.
            immediate (bool, optional): If `True`, commits the session
                immediately after saving the object. Defaults to `True`.
            session (AsyncSession, optional): An active asynchronous database
                session. If not provided, the method will create and manage its
                own session.
        """
        is_update = False
        for key in [k for k in self.__table__.columns.keys() if k in data.keys()]:
            if data[key] != getattr(self, key):
                setattr(self, key, data[key])
                is_update = True
        if is_update:
            log.debug("🛠️ Updating %s <%s>", type(self).__name__, self.guid)
            await save(self, immediate=immediate, session=session)
        else:
            log.debug(
                "🚧 Tried updating %s <%s> but no new values provided",
                type(self).__name__,
                self.guid,
            )

    @with_async_session
    async def delete(self, *, immediate: bool = True, session: AsyncSession) -> None:
        """Deletes this instance from the database, then flushes the session.

        Args:
            immediate (bool, optional): If `True`, flushes the session
                immediately after deleting the object. Defaults to `True`.
            session (AsyncSession, optional): An active asynchronous database
                session. If not provided, the method will create and manage its
                own session.
        """
        log.debug("🗑️ Deleting %s <%s>", type(self).__name__, self.guid)
        await session.delete(self)
        if immediate:
            await session.flush()

    def as_dict(self, excl: set[str] | None = None, to_js=False) -> dict[str, Any]:
        """Serializes this instance to dictionary.

        This uses the built-in dataclass `asdict()` method to recursively
        serialize this instance. We also pass this dictionary to a helper
        method which ensures all the native data objects it contains--like
        timestamps and paths--are converted to simpler forms.

        Args:
            excl: (set[str], optional): Keys to ignore.
            to_js (bool, optional): Convert dictionary keys to snakeCase for
                export to a JavaScript environment. Defaults to `False`.

        Returns:
            Serialized dictionary of values.
        """
        log.debug("📝 Serializing %s <%s>", type(self).__name__, self.guid)
        data = serialize(asdict(self), excl=excl, recursive=True, to_js=to_js)
        if "checksum" not in data.keys():
            data["checksum"] = create_checksum(json.dumps(data, sort_keys=True))
        return data


class StatusMixin(MappedAsDataclass, DeclarativeBase):
    """Mixin for status tracking.

    This mixin provides a simple way to track the status of an instance using
    predefined statuses. It includes a `status` field that can be set to one of
    several values, representing different stages in the lifecycle of the
    instance.

    Attributes:
        status (str): The current status of the instance, with a default value
            of 'PENDING'.
    """

    __abstract__ = True
    status: Mapped[str] = mapped_column(String(7), init=False, insert_default="PENDING")

    @with_async_session
    async def set_status(
        self, status: str, *, immediate: bool = True, session: AsyncSession
    ) -> None:
        """Sets the status of this instance.

        This method updates the status of the instance to one of the allowed
        values and saves the change to the database. The valid statuses are:

        - `'PENDING'`: Default status for new instances.
        - `'STARTED'`: Work on the instance has begun.
        - `'STOPPED'`: Reserved for future use.
        - `'SENDING'`: Work is finished but results are being uploaded.
        - `'SUCCESS'`: Work is completed and results are ready.
        - `'FAILURE'`: Reserved for future use.

        Args:
            status (str): The status to set for the instance.
            immediate (bool, optional): If `True`, commits the session
                immediately after saving the object. Defaults to `True`.
            session (AsyncSession, optional): An active asynchronous database
                session. If not provided, the method will create and manage its
                own session.

        Raises:
            ValueError: Provided status is not an accepted value.
        """
        status_set = ["PENDING", "STARTED", "SENDING", "SUCCESS"]
        if status.upper() not in status_set:
            status_set_str = (
                ", ".join(f"'{s}'" for s in status_set[:-1])
                + f", or {f"'{status_set[-1]}'"}"
            )
            raise ValueError(f"Invalid status '{status}', must be {status_set_str}")
        log.debug("🛠️ Setting status of %s to '%s'", type(self).__name__, status)
        self.status = status
        await save(self, immediate=immediate, session=session)

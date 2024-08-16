"""Database tools including session management, helper functions, and mixins.
"""

import base64
import logging
import math
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from random import random
from zoneinfo import ZoneInfo

import redis
from sqlalchemy import Column, DateTime, ForeignKey, String, Table, create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import declarative_base, declared_attr, scoped_session, sessionmaker

from orca import _config

log = logging.getLogger(__name__)


# SQLite database initialization
Base = declarative_base()
engine = create_engine(_config.DATABASE_URI)
SessionLocal = scoped_session(sessionmaker(bind=engine))


# Database session management
@contextmanager
def get_session():
    """Provide transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
    except SQLAlchemyError as e:
        log.exception(f"Error occurred while accessing the database: {e}")
        raise
    except Exception as e:
        log.exception(f"An unexpected error occurred: {e}")
        raise
    finally:
        session.close()


def get_redis_client():
    """Factory to connect to Redis and return a `StrictRedis` client.

    Uses socket specified by environment via `config.REDIS_SOCKET`.
    """
    for attempt in range(1, _config.DATABASE_RETRIES + 1):
        # Check for valid socket file
        if not _config.REDIS_SOCKET or not _config.REDIS_SOCKET.exists():
            raise ValueError("Error connecting to Redis socket")

        # Ping Redis, keep trying until we get a connection or hit max retries
        try:
            client = redis.StrictRedis(unix_socket_path=_config.REDIS_SOCKET.as_posix())
            client.ping()
            log.debug(f"Connected to Redis at {_config.REDIS_SOCKET}")
            return client
        except redis.ConnectionError as e:
            backoff_time = math.pow(2, attempt) + random()
            log.warning(
                f"Error connecting to Redis at {_config.REDIS_SOCKET}, "
                f"retrying ({attempt}/{_config.DATABASE_RETRIES}) "
                f"in {backoff_time:.2f} seconds: {e}"
            )
            time.sleep(backoff_time)
    raise redis.ConnectionError("Redis connection failed after multiple attempts")


def handle_sql_errors(func, *args, **kwargs):
    """SQL error handler.

    An active session must be passed via `**kwargs`.
    """

    session = kwargs.get("session")
    if not session or session is None:
        raise AttributeError("Tried to run SQL operation without a session")

    def try_rollback():
        if session and session.is_active and session.in_transaction():
            session.rollback()

    for attempt in range(1, _config.DATABASE_RETRIES + 1):
        try:
            return func(*args, **kwargs)

        except OperationalError as e:
            if attempt < _config.DATABASE_RETRIES:
                backoff_time = math.pow(2, attempt) + random()
                log.warning(
                    f"Error in operation, "
                    f"retrying ({attempt}/{_config.DATABASE_RETRIES}) "
                    f"in {backoff_time:.2f} seconds: {e}"
                )
                try_rollback()
                time.sleep(backoff_time)
            else:
                log.exception(f"Operation failed after multiple attempts: {e}")
                try_rollback()
                raise

        except SQLAlchemyError as e:
            log.exception(f"Unhandled SQL error, operation failed: {e}")
            try_rollback()
            raise


def with_session(func):
    """Decorator to manage local copy of `SessionLocal`.

    `SessionLocal` can be created externally and passed through the `session`
    keyword argument or it can be automatically instantiated here. Either way,
    operations will be passed along through `handle_sql_errors()`.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        session = kwargs.get("session")
        if session and session is not None:
            return handle_sql_errors(func, *args, **kwargs)
        with get_session() as session:
            kwargs["session"] = session
            return handle_sql_errors(func, *args, **kwargs)

    return wrapper


# Helper functions
def create_tables():
    """Populate database and create tables.

    This must be run at least once before anything else can happen.
    """
    Base.metadata.create_all(engine)


def create_uid():
    """Create url-safe UID.

    We're using UIDs instead of sequential integers because of the archival
    nature of the project. We want to be able to reference everything in a
    stable way over a long period of time, even at the cost of performance.
    """
    uid_b64 = base64.b32encode(uuid.uuid4().bytes)
    return uid_b64.rstrip(b"=").decode("ascii").lower()


def utcnow():
    """Future-proofed replacement for deprecated `datetime.utcnow()`."""
    return datetime.now(ZoneInfo("UTC"))


# Mixins
class CommonMixin:
    """Mixin for common item properties and functionality including ID, status,
    timestamp, and simple CRUD methods.
    """

    @declared_attr
    def __tablename__(cls):
        return f"{cls.__name__.lower()}s"

    uid = Column(String, primary_key=True, default=create_uid)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    @property
    def redis_key(self):
        """Get a key representing this item in the Redis database."""
        return f"orca:{self.__tablename__}:{self.uid}"

    @classmethod
    @with_session
    def get(cls, uid: str, session=None):
        """Get item by UID."""
        result = session.query(cls).filter_by(uid=uid).first()
        if not result:
            log.debug(f"No {cls.__tablename__} with uid {uid}")
        return result

    @classmethod
    @with_session
    def get_all(cls, session=None) -> list:
        """Get a lists of all rows in this table."""
        result = session.query(cls).all()
        if not result:
            log.debug(f"No rows in {cls.__tablename__}")
        return result

    @classmethod
    @with_session
    def get_total(cls, session=None):
        """Get total number of rows in this table."""
        result = session.query(cls).count()
        if not result or result == 0:
            log.debug(f"No {cls.__tablename__} or no rows in table")
        return int(result)

    @with_session
    def update(self, session=None, **kwargs):
        """Update columns based on values passed as keyword arguments."""
        save = False
        for key, value in kwargs.items():
            old_value = getattr(self, key)
            if hasattr(self, key) and old_value != kwargs[key]:
                log.debug(
                    f"Updating {self.__tablename__} with uid {self.uid} "
                    f"[{key}]: {old_value} -> {value}"
                )
                save = True
                setattr(self, key, value)
        if save:
            session.add(self)
            session.commit()
        else:
            log.debug(
                f"Tried updating {self.__tablename__} with uid {self.uid} "
                f"but no new values were passed"
            )

    @with_session
    def delete(self, session=None):
        """Delete this row from the table."""
        log.debug(f"Deleting {self.__tablename__} with uid {id}")
        session.delete(self)
        session.commit()

    def as_dict(self):
        """Serialize table to `dict`.

        Automatically converts any `DateTime` columns to `str` using
        `.isoformat()`. Since SQLite doesn't support TZ-awareness, we'll assume
        these are stored in UTC and attach `'+00:00'` to the end of them. That
        way JS can correct them based on client settings, eg.
        """
        rows = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = f"{value.isoformat()}Z"
            rows[column.name] = value
        return rows


class StatusMixin:
    """Mixin for status tracking. Includes `self.status` property and
    `self.set_status()` method.
    """

    status = Column(String, nullable=False, default="PENDING")

    @with_session
    def set_status(self, status, session=None):
        """Set status of this instance.

        Possible values are:
        - `'PENDING'`: Default for all instances.
        - `'STARTED'`: Work has started on this table.
        - `'SENDING'`: Work has finished but results are still being uploaded.
        - `'SUCCESS'`: Work has finished and results are ready.
        - `'FAILURE'`: Something went wrong. We'll need to restart.
        """
        status_set = {"PENDING", "STARTED", "SENDING", "SUCCESS", "FAILURE"}
        if status not in status_set:
            log.warning(
                f"Tried setting status of {self.__tablename__} with uid {self.uid} to "
                f"{status}; status must be one of {', '.join(status_set)}"
            )
            return

        log.debug(
            f"Setting status of {self.__tablename__} with uid {self.uid} to {status}"
        )
        self.status = status
        session.add(self)
        session.commit()


# Many-many table to correlate corpuses with specific document versions.
documents_corpuses = Table(
    "documents_corpuses",
    Base.metadata,
    Column("corpus_hash", String, ForeignKey("corpuses.hash_value"), primary_key=True),
    Column("document_uid", String, ForeignKey("documents.uid"), primary_key=True),
)


# Many-many table to correlate searches with the documents they find.
documents_searches = Table(
    "documents_searches",
    Base.metadata,
    Column("search_uid", String, ForeignKey("searches.uid"), primary_key=True),
    Column("document_uid", String, ForeignKey("documents.uid"), primary_key=True),
)

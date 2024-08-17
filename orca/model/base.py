"""Database tools including session management, helper functions, and mixins.
"""

import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from random import random

import redis
from slugify import slugify
from sqlalchemy import Column, DateTime, ForeignKey, String, Table, create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import declarative_base, declared_attr, scoped_session, sessionmaker

from orca import _config
from orca._helpers import create_uid, utc_now

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
            backoff_time = attempt**2 + random()
            log.warning(
                f"Error connecting to Redis at {_config.REDIS_SOCKET}, "
                f"retrying ({attempt}/{_config.DATABASE_RETRIES}) "
                f"in {backoff_time:.2f} seconds: {e}"
            )
            time.sleep(backoff_time)

    raise redis.ConnectionError("Redis connection failed after multiple attempts")


def handle_sql_errors(func):
    """SQL error handler decorator. An active session must be passed in through
    the keyword arguments.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not (session := kwargs.get("session")):
            raise AttributeError("No session provided for SQL operation")

        def try_rollback(exc):
            if session.is_active and session.in_transaction():
                log.warning(f"Rolling back transaction: {exc}")
                session.rollback()

        for attempt in range(1, _config.DATABASE_RETRIES + 1):
            try:
                return func(*args, **kwargs)

            # Operation errors usually signify a collision error or something
            # else we ought to be able to retry. Give it another shot then
            # apply an exponential backoff.
            except OperationalError as e:
                backoff_delay = attempt**2 + random()
                log.warning(
                    "Error in database operation ,"
                    f"retrying ({attempt}/{_config.DATABASE_RETRIES}) "
                    f"in {backoff_delay:.2f} seconds"
                )
                try_rollback(e)

        raise OperationalError("Operation failed after multiple attempts")

    return wrapper


def with_session(func):
    """Decorator to manage local copy of `SessionLocal`.

    `SessionLocal` can be created externally and passed through the `session`
    keyword argument or it can be automatically instantiated here. Either way,
    operations will be passed along through `handle_sql_errors()`.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if session := kwargs.get("session"):
            return handle_sql_errors(func)(*args, **kwargs)
        with get_session() as session:
            kwargs["session"] = session
            return handle_sql_errors(func)(*args, **kwargs)

    return wrapper


# Helper functions
def create_tables():
    """Populate database and create tables.

    This must be run at least once before anything else can happen.
    """
    Base.metadata.create_all(engine)


# Mixins
class CommonMixin:
    """Mixin for common item properties and functionality including ID, status,
    timestamp, and simple CRUD methods.
    """

    @declared_attr
    def __tablename__(cls):
        return f"{cls.__name__.lower()}s"

    uid = Column(String(22), primary_key=True, default=create_uid)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    tags = Column(String(255), default="")
    comments = Column(String, default="")

    @property
    def redis_key(self):
        """Get a key representing this item in the Redis database."""
        return (
            f"{slugify(_config.APP_NAME)}"
            f":{slugify(self.__tablename__)}"
            f":{slugify(self.uid)}"
        )

    @classmethod
    @with_session
    def get(cls, uid: str, session=None):
        """Get item by UID."""
        if not (result := session.query(cls).filter_by(uid=uid).first()):
            log.debug(f"No {cls.__tablename__} with uid {uid}")
        return result

    @classmethod
    @with_session
    def get_all(cls, session=None) -> list:
        """Get a list of all items in this table."""
        if not (result := session.query(cls).all()):
            log.debug(f"No items in {cls.__tablename__}")
        return result

    @classmethod
    @with_session
    def get_total(cls, session=None):
        """Get total number of items in this table."""
        if not (result := session.query(cls).count()):
            log.debug(f"No {cls.__tablename__} or no items in table")
        return int(result)

    @with_session
    def update(self, session=None, **kwargs):
        """Update columns based on values passed as keyword arguments."""
        save = False
        for key, value in kwargs.items():
            if hasattr(self, key) and (old_value := getattr(self, key)) != kwargs[key]:
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
        """Serialize table to `dict`."""
        rows = {}
        for column in self.__table__.columns:
            if isinstance(value := getattr(self, column.name), datetime):
                value = value.replace(tzinfo=timezone.utc).isoformat()
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
        statuses = {"PENDING", "STARTED", "SENDING", "SUCCESS", "FAILURE"}
        if status not in statuses:
            log.warning(
                f"Tried setting status of {self.__tablename__} with uid {self.uid} to "
                f"{status}; status must be one of {', '.join(statuses)}"
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
    "corpus_documents",
    Base.metadata,
    Column(
        "corpus_checksum", String(8), ForeignKey("corpuses.checksum"), primary_key=True
    ),
    Column("document_uid", String(22), ForeignKey("documents.uid"), primary_key=True),
)


# Many-many table to correlate searches with the documents they find.
documents_searches = Table(
    "search_documents",
    Base.metadata,
    Column("search_uid", String(22), ForeignKey("searches.uid"), primary_key=True),
    Column("document_uid", String(22), ForeignKey("documents.uid"), primary_key=True),
)

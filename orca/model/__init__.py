"""
This submodule provides the core ORM models and utilities for managing
documents, search results, and database interactions within the ORCA system. It
consolidates tools for asynchronous session management, base model classes, and
specialized models for handling documents, corpuses, and search results. It
ensures consistency and integrity in database operations, while offering a
robust foundation for interacting with the various artifacts and metadata
within ORCA's corpus.
"""

from orca.model.base import Base, StatusMixin  # noqa: F401
from orca.model.corpus import Corpus  # noqa: F401
from orca.model.db import (  # noqa: F401
    db_lock,
    get_async_engine,
    get_async_session,
    init_async_engine,
    save,
    teardown_async_engine,
    with_async_session,
)
from orca.model.document import Document, Scan  # noqa: F401
from orca.model.search import Megadoc, Search  # noqa: F401

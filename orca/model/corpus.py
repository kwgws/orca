"""
Module for managing document corpuses within the application.

This module provides the `Corpus` class and associated functionality for taking
snapshots of document collections, which is crucial for ensuring the
consistency and integrity of search results over time. By capturing a specific
set of documents at a moment in time, the `Corpus` class allows for versioning,
comparison, and generation of diffs, making it possible to track changes and
maintain historical accuracy.
"""

import asyncio
import logging
from pathlib import Path

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from orca import config
from orca.helpers import create_checksum

from .base import Base, with_async_session
from .document import Document

log = logging.getLogger(__name__)


_corpus_documents = Table(
    "corpus_documents",
    Base.metadata,
    Column("corpus_guid", ForeignKey("corpuses.guid")),
    Column("document_guid", ForeignKey("documents.guid")),
)
"""Many-to-many relationship table specifying which `Document`s belong to which
`Corpus`es.
"""


class Corpus(Base):
    """Represents a collection of documents at a specific point in time.

    The `Corpus` class allows for the creation of snapshots of document sets,
    enabling version comparison and diff generation. This is crucial for
    maintaining the integrity of search results, as any modifications to the
    corpus will alter the outcome of those searches.

    Attributes:
        checksum (str): Checksum of all the text contained within this `Corpus`'
            list of `Document`s.
        documents (list[Document]): List of `Document`s contained within this
            `Corpus`.
        document_count (int, optional): Cached count of all the `Document`s
            contained within this `Corpus`. Provided automatically but can be
            overridden for edge cases or testing.
    """

    checksum: Mapped[str] = mapped_column(String(8))
    documents: Mapped[list[Document]] = relationship(
        secondary=_corpus_documents, lazy="selectin"
    )
    document_count: Mapped[int] = mapped_column(default=0)

    @classmethod
    @with_async_session
    async def create(
        cls,
        *,
        data_path: Path = config.data_path,
        immediate: bool = True,
        session: AsyncSession,
    ) -> "Corpus":
        """Creates and persists a new corpus of all current documents.

        This method retrieves all documents, sorts them by their creation date,
        and generates a unique checksum based on the serialized content of each
        document. The resulting `Corpus` object, containing the checksum, the
        document list, and the document count, is saved to the database.

        Args:
            data_path (Path, optional): Base data path where metadata files are
                stored. This is usually provided by `config.data_path` but can
                be overridden here for edge cases or testing.
            immediate (bool, optional): If `True`, the session is committed
                after saving the `Corpus`. Default is `True`.
            session (AsyncSession, optional): An active asynchronous database
                session. If not provided, the method will create and manage its
                own session.

        Returns:
            The newly created `Corpus` object.
        """
        documents: list[Document] = await Document.get_all(session=session)
        document_count = len(documents)

        log.info("🧮 Generating checksum for %d documents", document_count)
        documents.sort(key=lambda doc: doc.created_at)
        raw = "".join(
            await asyncio.gather(*(d.get_text_async(data_path) for d in documents))
        )
        checksum = create_checksum(raw)

        return await super().create(
            checksum=checksum,
            documents=documents,
            document_count=document_count,
            immediate=immediate,
            session=session,
        )

"""Model to track search results and megadocs, anything related to artifacts
produced by ORCA as intended output.
"""

import logging
import os

import regex as re
from slugify import slugify
from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from orca import config
from orca.model.base import (
    Base,
    CommonMixin,
    StatusMixin,
    get_utcnow,
    get_uuid,
    result_table,
    with_session,
)
from orca.model.corpus import Corpus
from orca.model.document import Document

log = logging.getLogger(config.APP_NAME)


class Search(Base, CommonMixin, StatusMixin):
    """Store searches, their progress, and their results."""

    __tablename__ = "searches"
    search_str = Column(String, nullable=False)
    documents = relationship(
        "Document", back_populates="searches", secondary=result_table
    )
    megadocs = relationship(
        "Megadoc", back_populates="search", cascade="all, delete-orphan"
    )

    @classmethod
    @with_session
    def create(cls, search_str: str, session=None):
        """Create a new instance and commit it to the table."""
        search = cls(search_str=search_str)

        # Tag with most recent hash value
        corpus = Corpus.get_latest(session=session)
        search.corpus = corpus
        corpus.searches.append(search)
        session.add(corpus)

        session.add(search)
        session.commit()
        return search

    @with_session
    def add_document(self, document: Document, session=None):
        """Add a document to this search's results."""
        if document in self.documents:
            log.warning(f"Tried re-adding {document.id} to `{self.search_str}`")
            return

        # Add the document to our list.
        self.documents.append(document)
        session.add(self)
        document.searches.append(self)
        session.add(document)
        session.commit()
        return document

    @with_session
    def add_megadoc(self, filetype: str, session=None):
        """Create a megadoc of a given filetype for this search."""
        if filetype in {x.filetype for x in self.megadocs}:
            log.warning(f"Tried re-creating {filetype} for `{self.search_str}`")
            return

        megadoc = Megadoc(search=self, filetype=filetype)
        session.add(megadoc)
        self.megadocs.append(megadoc)
        session.add(self)
        session.commit()
        return megadoc

    def as_dict(self):
        rows = super().as_dict()
        rows["corpus"] = {"hash": self.corpus.hash, "color": self.corpus.hash_color}
        rows.pop("corpus_id")
        rows["results"] = len(self.documents)
        rows["megadocs"] = [md.as_dict() for md in self.megadocs]
        return rows


class Megadoc(Base, CommonMixin, StatusMixin):
    """A megadoc is text file containing the results of every document matching
    our search. This is the main thing we're here to produce.
    """

    id = Column(String, primary_key=True)
    filetype = Column(String, nullable=False, default=".txt")
    filename = Column(String)
    path = Column(String)
    url = Column(String)
    search_id = Column(String, ForeignKey("searches.id"), nullable=False)
    search = relationship("Search", back_populates="megadocs")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # We need the ID to generate paths so we'll do it manually here
        self.id = get_uuid()

        # Generate the paths
        timestamp = re.sub(
            r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}).*",
            r"\1\2\3-\4\5\6",
            f"{get_utcnow().isoformat()}",
        )
        self.filename = f"{slugify(self.search.search_str)}_{timestamp}Z{self.filetype}"
        self.path = f"{config.MEGADOC_PATH / self.filename}"
        if os.path.exists(self.path):
            log.warning(f"Megadoc file already exists, could be error: {self.path}")
        self.url = f"{config.CDN_URL}/{self.path}"

    @property
    def filesize(self):
        """Size of megadoc file in bytes. Returns 0 if no file."""
        try:
            return os.path.getsize(self.path)
        except OSError as e:
            log.warning(f"Error finding size of file {self.path}: {e}")
            return 0

    def as_dict(self):
        rows = super().as_dict()
        rows.pop("filename")
        rows.pop("path")
        rows.pop("search_id")
        rows["filesize"] = self.filesize
        return rows

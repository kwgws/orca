"""Model to track search results and megadocs, anything related to artifacts
produced by ORCA as intended output.
"""

import logging

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from orca import _config
from orca.model.base import (
    Base,
    CommonMixin,
    StatusMixin,
    documents_searches,
    get_redis_client,
    with_session,
)
from orca.model.corpus import Corpus
from orca.model.document import Document
from orca.model.megadoc import Megadoc

log = logging.getLogger(__name__)
r = get_redis_client()


class Search(Base, CommonMixin, StatusMixin):
    """Store searches, their progress, and their results."""

    __tablename__ = "searches"
    search_str = Column(String, nullable=False)
    documents = relationship(
        "Document", back_populates="searches", secondary=documents_searches
    )
    megadocs = relationship(
        "Megadoc", back_populates="search", cascade="all, delete-orphan"
    )
    corpus_uid = Column(String, ForeignKey("corpuses.hash_value"), nullable=False)
    corpus = relationship("Corpus", back_populates="searches")

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
            log.warning(f"Tried re-adding {document.uid} to `{self.search_str}`")
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
        rows.pop("corpus_uid")
        rows["results"] = len(self.documents)
        rows["megadocs"] = [md.as_dict() for md in self.megadocs]
        return rows

"""Model to track search results and megadocs, anything related to artifacts
produced by ORCA as intended output.
"""

import logging

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from orca.model.base import (
    Base,
    CommonMixin,
    StatusMixin,
    documents_searches,
    with_session,
)
from orca.model.corpus import Corpus
from orca.model.document import Document
from orca.model.megadoc import Megadoc

log = logging.getLogger(__name__)


class Search(Base, CommonMixin, StatusMixin):
    """Store searches, their progress, and their results."""

    __tablename__ = "searches"
    search_str = Column(String(255), nullable=False)
    corpus_checksum = Column(String(8), ForeignKey("corpuses.checksum"), nullable=False)
    corpus = relationship("Corpus", back_populates="searches")
    documents = relationship(
        "Document", back_populates="searches", secondary=documents_searches
    )
    megadocs = relationship(
        "Megadoc", back_populates="search", cascade="all, delete-orphan"
    )

    @classmethod
    @with_session
    def create(cls, search_str: str, session=None):
        """Create a new instance and commit it to the table."""
        search = cls(search_str=search_str)

        # Tag with most recent checksum
        corpus = Corpus.get_latest(session=session)
        corpus.searches.append(search)
        search.corpus = corpus

        session.add_all([corpus, search])
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
        document.searches.append(self)
        session.add_all([self, document])
        session.commit()
        return document

    @with_session
    def add_megadoc(self, filetype: str, session=None):
        """Create a megadoc of a given filetype for this search."""
        if filetype in {x.filetype for x in self.megadocs}:
            log.warning(f"Tried re-creating {filetype} for `{self.search_str}`")
            return

        megadoc = Megadoc(search=self, filetype=filetype)
        self.megadocs.append(megadoc)
        session.add_all([self, megadoc])
        session.commit()
        return megadoc

    def as_dict(self):
        rows = super().as_dict()
        rows.pop("corpus_checksum")
        rows["results"] = len(self.documents)
        rows["megadocs"] = [
            doc.as_dict() for doc in sorted(self.megadocs, key=lambda doc: doc.filetype)
        ]
        return rows

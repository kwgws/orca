import hashlib
import logging

from sqlalchemy import Column, DateTime, Integer, String, desc
from sqlalchemy.orm import relationship

from orca import config
from orca.model.base import Base, corpus_table, get_utcnow, with_session
from orca.model.document import Document

log = logging.getLogger(config.APP_NAME)


class Corpus(Base):
    """We can use Corpuses to take a snapshot of the collection, compare
    versions, and generate diffs. This is important to maintain the integrity
    of a given set of search results, since any changes to the corpus will
    necessarily change those results.
    """

    __tablename__ = "corpuses"
    hash = Column(String, primary_key=True)
    created = Column(DateTime, nullable=False, default=get_utcnow)
    total = Column(Integer, nullable=False)
    documents = relationship(
        "Document", back_populates="corpuses", secondary=corpus_table
    )
    searches = relationship(
        "Search", back_populates="corpus", cascade="all, delete-orphan"
    )

    @classmethod
    @with_session
    def create(cls, session=None):
        """Take a snapshot of the current tables and save."""
        documents = Document.get_all(session=session)
        total = len(documents)

        # Generate and store hash value
        log.info(f"Hashing {total} documents")
        hash = hashlib.sha256(
            "".join([d.id for d in documents]).encode(),
            usedforsecurity=False,
        ).hexdigest()

        log.info(f"Adding {total} documents to corpus")
        corpus = cls(hash=hash, documents=documents, total=len(documents))
        session.add(corpus)
        for i, document in enumerate(documents):
            document.corpus = corpus
            session.add(document)
            if (i + 1) % config.DATABASE_BATCH_SIZE == 0 or (i + 1) == total:
                log.info(f"Adding documents to corpus ({i + 1}/{total})")
                session.commit()

        log.info("Done creating corpus")
        return corpus

    @classmethod
    @with_session
    def get_latest(cls, session=None):
        """Return the most recent corpus."""
        result = session.query(cls).order_by(desc(cls.created)).first()
        if not result:
            log.warning("Tried getting most recent corpus snapshot but none exist")
        return result

    def as_dict(self):
        return {
            "hash": self.hash,
            "color": "#" + self.hash[:6],
            "documents": self.total,
            "searches": [s.as_dict() for s in self.searches],
        }

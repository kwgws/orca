import hashlib
import logging

from sqlalchemy import Column, String, desc
from sqlalchemy.orm import relationship

from orca import config
from orca.model.base import Base, CommonMixin, corpus_table, with_session
from orca.model.document import Document

log = logging.getLogger(config.APP_NAME)


class Corpus(Base, CommonMixin):
    """We can use Corpuses to take a snapshot of the collection, compare
    versions, and generate diffs. This is important to maintain the integrity
    of a given set of search results, since any changes to the corpus will
    necessarily change those results.
    """

    __tablename__ = "corpuses"
    documents = relationship(
        "Document", back_populates="corpuses", secondary=corpus_table
    )
    searches = relationship(
        "Search", back_populates="corpus", cascade="all, delete-orphan"
    )
    hash = Column(String, unique=True)
    hash_color = Column(String)

    @classmethod
    @with_session
    def create(cls, session=None):
        """Take a snapshot of the current tables and save."""
        documents = Document.get_all(session=session)
        total = len(documents)
        log.info(
            f"Creating a corpus snapshot and hash value for {total} documents,"
            " this may take some time"
        )

        corpus = cls(documents=documents)

        # Generate and store hash value
        raw = "".join([d.id for d in corpus.documents])
        corpus.hash = hashlib.sha256(raw.encode(), usedforsecurity=False).hexdigest()
        corpus.hash_color = f"#{corpus.hash[:6]}"

        session.add(corpus)
        log.info(f"Adding {total} documents to corpus snapshot")

        for i, document in enumerate(documents):
            document.corpus = corpus
            session.add(document)
            if (i + 1) % config.APP_NAME0 == 0 or (i + 1) == total:
                log.info(f"Adding document {i + 1}/{total} to corpus snapshot")
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
        rows = super().as_dict()
        rows["documents"] = len(self.documents)
        rows["searches"] = [s.as_dict() for s in self.searches]
        return rows

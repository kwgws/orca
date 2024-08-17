import logging
from datetime import timezone

from sqlalchemy import Column, DateTime, Integer, String, desc
from sqlalchemy.orm import relationship

from orca import _config
from orca._helpers import create_crc, utc_now
from orca.model.base import Base, documents_corpuses, with_session
from orca.model.document import Document

log = logging.getLogger(__name__)


class Corpus(Base):
    """We can use Corpuses to take a snapshot of the collection, compare
    versions, and generate diffs. This is important to maintain the integrity
    of a given set of search results, since any changes to the corpus will
    necessarily change those results.
    """

    __tablename__ = "corpuses"
    checksum = Column(String(8), primary_key=True)
    total_documents = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    comments = Column(String, default="")
    documents = relationship(
        "Document", back_populates="corpuses", secondary=documents_corpuses
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
        log.info(f"Adding {total} documents to corpus")

        # Generate and checksum
        log.info("Generating checksum, this may take some time")
        checksum = create_crc("".join([d.content for d in documents]))
        log.info(f"Checksum: {checksum}")
        corpus = cls(checksum=checksum, documents=documents, total_documents=total)

        session.add(corpus)
        session.commit()

        # Go back and add our corpus to each and every document so we can use
        # it to cross-reference later.
        for i, document in enumerate(documents):
            document.corpus = corpus
            session.add(document)
            if (i + 1) % _config.DATABASE_BATCH_SIZE == 0 or (i + 1) == total:
                log.info(f"Adding document to corpus ({i + 1}/{total})")
                session.commit()

        log.info("Done creating corpus")
        return corpus

    @classmethod
    @with_session
    def get_all(cls, session=None):
        if not (result := session.query(cls).order_by(desc(cls.created_at)).all()):
            log.warning("Tried getting all corpuses but none exist")
        return result

    @classmethod
    @with_session
    def get_latest(cls, session=None):
        """Return the most recent corpus."""
        if not (result := session.query(cls).order_by(desc(cls.created_at)).first()):
            log.warning("Tried getting most recent corpus but none exist")
        return result

    def as_dict(self):
        return {
            "checksum": self.checksum,
            "total_documents": self.total_documents,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "searches": [s.as_dict() for s in self.searches],
        }

"""Model to track documents, anything to do with ORCA's corpus.
"""

import logging  # noqa: F401
from pathlib import Path

from dateutil.parser import parse as parse_datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, inspect
from sqlalchemy.orm import relationship

from orca_api import config

from .db import (  # noqa: F401
    Base,
    CommonMixin,
    corpus_table,
    result_table,
    with_session,
)

log = logging.getLogger("orca")


class Image(Base, CommonMixin):
    """Each document is represented first by an immutable image file. These
    won't change as the document itself is revised.

    We need to be able to make exceptions, though, for documents which might
    come to us _without_ an image file; that might be imported eg as text only.
    Nevertheless, for organizational purposes, this is where we'll store as the
    base object.
    """

    stem = Column(String)
    title = Column(String)
    album = Column(String)
    index = Column(Integer)
    media_archive = Column(String)
    media_collection = Column(String)
    media_box = Column(String)
    media_folder = Column(String)
    media_type = Column(String)
    media_created = Column(DateTime)
    image_path = Column(String)
    image_url = Column(String)
    thumb_url = Column(String)
    documents = relationship(
        "Document", back_populates="image", cascade="all, delete-orphan"
    )

    def __init__(self, *args, **kwargs):
        # Get a list of keys and filter out anything we want here
        mapper = inspect(self.__class__)
        columns = {column.key for column in mapper.columns}
        img_kwargs = {key: kwargs.pop(key) for key in columns if key in kwargs}

        """Create an image and its first document."""
        super().__init__(*args, **img_kwargs)

        # Otherwise pass the other kwargs along to our first document
        document = Document(**kwargs)
        document.image = self
        self.documents.append(document)

    @classmethod
    @with_session
    def create_from_file(cls, path, session=None, batch_only=False):
        """Commit a new Image/Document to the database. Use `batch_only` to
        indicate we only want to add to our current `session` rather than
        commiting outright.

        This is based on a very specific kind of filename, which typically
        looks like this: `000001_2022-09-27_13-12-42_IMG_5992.json`. The data
        is separated by underscores. The first part is the index. The second
        two are the date and time. Any remaining parts are the title.
        """

        if not isinstance(path, Path):
            path = Path(path)  # The pathlib module is helpful here
        stem = path.stem
        split = stem.split("_")
        album = path.parent.name

        # Parse the datetime from the filename using dateutil
        timestamp = parse_datetime(f"{split[1]} {split[2].replace('-', ':')}")

        # These paths need to be relative so we can make them portable
        json_path = Path(config.BATCH_NAME) / "json" / album / f"{stem}.json"
        text_path = Path(config.BATCH_NAME) / "text" / album / f"{stem}.txt"
        image_path = Path("img") / album / f"{stem}.webp"

        image = Image(
            index=int(split[0]),
            title="_".join(split[3:]),
            album=album,
            batch=config.BATCH_NAME,
            json_path=f"{json_path}",
            json_url=f"{config.CDN_URL}/{json_path}",
            text_path=f"{text_path}",
            text_url=f"{config.CDN_URL}/{text_path}",
            image_path=f"{image_path}",
            image_url=f"{config.CDN_URL}/{image_path}",
            thumb_url=f"{config.CDN_URL}/thumbs/{album}/{stem}.webp",
            created=timestamp,
        )
        session.add(image)
        document = image.documents[0]
        session.add(document)
        if not batch_only:
            session.commit()
        return image

    def as_dict(self):
        rows = super().as_dict()
        rows.pop("image_path")
        rows["documents"] = [doc.as_dict() for doc in self.documents]
        return rows


class Document(Base, CommonMixin):
    """Documents here represent rather a specific revision of a given document.
    This is useful if we want to change something later: if we want to revise
    the text, or run the image through a diffferent model, etc.

    A specific collection of documents will be stored in a Corpus. This should
    eventually let us do versioning and diff with our queries.
    """

    batch = Column(String)
    json_path = Column(String)
    json_url = Column(String)
    text_path = Column(String)
    text_url = Column(String)
    image_id = Column(String, ForeignKey("images.id"), nullable=False)
    image = relationship("Image", back_populates="documents")
    corpuses = relationship(
        "Corpus", back_populates="documents", secondary=corpus_table
    )
    searches = relationship(
        "Search", back_populates="documents", secondary=result_table
    )

    def as_dict(self):
        rows = super().as_dict()
        rows.pop("json_path")
        rows.pop("text_path")
        rows.pop("image_id")
        rows["corpuses"] = [c.id for c in self.corpuses]
        return rows
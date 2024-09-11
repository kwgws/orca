"""
Models to track artifacts and related metadata within ORCA's corpus.

This module provides ORM models for managing scans and documents within ORCA's
corpus. Each `Scan` represents an immutable image file associated with an
artifact, along with its metadata. The `Document` model tracks specific
revisions of text or metadata associated with these scans, allowing for
versioning and historical record-keeping.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Self

from dateutil.parser import ParserError
from dateutil.parser import parse as parse_datetime
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from unidecode import unidecode

from orca import config
from orca.helpers import dt_old
from orca.model.base import Base
from orca.model.db import with_async_session

log = logging.getLogger(__name__)


class Scan(Base):
    """Represents an immutable image file associated with an artifact.

    This model stores metadata for the base image file of an artifact and
    serves as its primary reference point. Every artifact in ORCA's corpus must
    have at least one `Scan` associated with it and at least one `Document`
    associated with that `Scan`.

    Attributes:
        stem (str): The original filename without extension. This can be used
            to construct other filenames/URLs or to parse essential metadata.
            Typically formatted as: `000001_2022-09-27_13-12-42_image_5992`,
            where:
            - `000001` is the album index.
            - `2022-09-27_13-12-42` is the scan timestamp.
            - `image_5992` is the scan title.
        album (str): The album name, used to organize `Scan` objects into
            folders. Typically based on the year and month of the scan, though
            other configurations are possible.
        album_index (int): The index of the `Scan` within its album.
        title (str): The title of the `Scan`, usually derived from the original
            file stem.
        path (str, optional): The relative path to the original image file.
        url (str, optional): The full URL of the image file.
        thumb_url (str, optional): The full URL of the thumbnail image.
        scanned_at (datetime, optional): The timestamp of when the image was
            taken or scanned, in UTC. Defaults to January 1, 1970.
        media_archive (str, optional): The archive or institution holding the
            original artifact.
        media_collection (str, optional): The collection within the archive.
        media_box (str, optional): The box name or number within the collection.
        media_folder (str, optional): The folder name or number within the box.
        media_type (str, optional): A description of the type of artifact (e.g.,
            photograph, manuscript).
        media_created_at (datetime, optional): The timestamp of when the
            artifact was originally created. Defaults to January 1, 1970.
    """

    stem: Mapped[str] = mapped_column(String(255))
    album: Mapped[str] = mapped_column(String(255))
    album_index: Mapped[int] = mapped_column()
    title: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(String(255), default="")
    thumb_url: Mapped[str] = mapped_column(String(255), default="")
    scanned_at: Mapped[datetime] = mapped_column(default_factory=dt_old)
    media_archive: Mapped[str] = mapped_column(String(255), default="")
    media_collection: Mapped[str] = mapped_column(String(255), default="")
    media_box: Mapped[str] = mapped_column(String(255), default="")
    media_folder: Mapped[str] = mapped_column(String(255), default="")
    media_type: Mapped[str] = mapped_column(String(255), default="")
    media_created_at: Mapped[datetime] = mapped_column(default_factory=dt_old)

    @with_async_session
    async def delete(self, *, session: AsyncSession) -> None:
        """Deletes this `Scan` instance.

        This method will also delete any associated `Document` objects,
        ensuring that all related data is removed from the database.

        Args:
            session (AsyncSession, optional): An active asynchronous database
                session. If not provided, the method will create and manage its
                own session.
        """
        log.debug("🗑️ Deleting Scan <%s> and all associated Documents", self.guid)
        for doc in await Document.get_all_for_scan(self, session=session):
            await doc.delete(session=session)
        await session.delete(self)
        await session.flush()


class Document(Base):
    """Represents a specific revision of a document within ORCA's corpus.

    The `Document` model captures revisions of a document, allowing for
    versioning and tracking changes over time. This is useful for maintaining
    different iterations of an artifact, whether changes involve text
    corrections or reprocessing the associated image. `Document` objects are
    grouped within a `Corpus`, facilitating version control and diffing.

    Attributes:
        scan_guid (str): The GUID of this `Document`'s parent `Scan`.
        scan (Scan): A mapped relationship to the parent `Scan`.
        batch_name (str, optional): `Document` objects can be organized by
            batch on disk to help keep different versions organized before they
            are sorted by `Corpus` in the database. The default batch is "00".
        json_path (str, optional): The path to this `Document`'s associated
            JSON metadata, usually the raw output from an OCR model.
        json_url (str, optional): The URL of the stored JSON metadata.
        text_path (str, optional): The path to this `Document`'s associated
            text content, usually the processed text from the OCR model.
        text_url (str, optional): The URL of the stored text content.
    """

    scan_guid: Mapped[str] = mapped_column(
        String(22), ForeignKey("scans.guid"), init=False
    )
    scan: Mapped["Scan"] = relationship(lazy="joined")
    batch_name: Mapped[str] = mapped_column(String(255), default="00")
    json_path: Mapped[str] = mapped_column(String(255), default="")
    json_url: Mapped[str] = mapped_column(String(255), default="")
    text_path: Mapped[str] = mapped_column(String(255), default="")
    text_url: Mapped[str] = mapped_column(String(255), default="")

    def get_json(self, data_path: Path = config.data_path) -> dict[str, Any]:
        """Retrieves JSON metadata.

        This coroutine retrieves the JSON metadata associated with the
        `Document`. If the file is missing or cannot be read, an empty
        dictionary is returned.

        Args:
            data_path (Path, optional): Base data path where metadata files are
                stored. This is usually provided by `config.data_path` but can
                be overridden here for edge cases or testing.

        Returns:
            The JSON metadata or an empty dictionary on error.
        """
        path = data_path / self.json_path
        log.debug("📝 Getting JSON metadata for Document <%s> at %s", self.guid, path)
        try:
            content = unidecode(path.read_text().strip())
            return json.loads(content) or {}
        except (FileNotFoundError, PermissionError, json.JSONDecodeError):
            log.warning(f"🚧 Cannot read JSON metadata from file '{path}'")
            return {}

    def get_text(self, data_path: Path = config.data_path) -> str:
        """Retrieves text content.

        This coroutine retrieves the text content associated with the
        `Document`. If the file is missing or cannot be read, an empty string
        is returned.

        Args:
            data_path (Path, optional): Base data path where metadata files are
                stored. This is usually provided by `config.data_path` but can
                be overridden here for edge cases or testing.

        Returns:
            The text content or an empty string on error.
        """
        path = data_path / self.text_path
        log.debug("📝 Getting text content for Document <%s> at %s", self.guid, path)
        try:
            return unidecode(path.read_text().strip())
        except (FileNotFoundError, PermissionError):
            log.warning(f"🚧 Cannot read text from file '{path}'")
            return ""

    @classmethod
    @with_async_session
    async def get_all_for_scan(cls, scan: Scan, *, session: AsyncSession) -> list[Self]:
        """Retrieves all `Document` instances associated with a given `Scan`.

        This method fetches all documents that are associated with the
        specified `Scan` instance from the database. We provide this as a
        method instead of a `relationship` column in order to avoid recursion.

        Args:
            scan (Scan): The `Scan` instance for which to find associated
                documents.
            session (AsyncSession, optional): An active asynchronous database
                session. If not provided, the method will create and manage its
                own session.
        Returns:
            A list of `Document` instances associated with the given `Scan`.
        """
        log.debug("🔍 Getting all Documents for Scan <%s>", scan.guid)
        result = await session.execute(select(cls).where(cls.scan_guid == scan.guid))
        return [doc for doc in result.scalars().all()] or []

    @classmethod
    @with_async_session
    async def create_from_file(
        cls,
        path: str | Path,
        scan: Scan | None,
        *,
        batch_name: str = config.batch_name,
        immediate: bool = True,
        session: AsyncSession,
    ) -> Self:
        """Creates and persists a new `Document` to the database.

        This method processes a file based on its filename and creates a
        `Document` to represent it in the database. If  no `Scan` is provided,
        it creates one of those as well. The filename **must** follow **this**
        specific format:

        >>> ".../album/000001_2022-09-27_13-12-42_image_5992.json"

        Setting `immediate` to `False` will not commit the session. This is so
        that we can add documents in bulk and only commit at intervals.

        **Note**: This method does not verify if the file actually exists! It
        only parses the text of the file path. This is an intentional
        workaround for edge cases and testing.

        Args:
            path (str or Path): The file path to parse.
            scan (Scan, optional): An existing `Scan` object to associate with
                the `Document`. If not provided, a new `Scan` will be created.
            batch_name (str, optional): Batch name, used to construct paths.
                This is usually provided by `config.data_path` but can be
                overridden here for edge cases or testing.
            immediate (bool, optional): If `True`, the session is committed
                after saving the `Scan` and `Document`. Default is `True`.
            session (AsyncSession, optional): An active asynchronous database
                session. If not provided, the method will create and manage its
                own session.

        Returns:
            The new `Document` object. Its associated scan can be accessed via
                `doc.scan`.

        Raises:
            TypeError: Filename could not be parsed; likely the format is not
                correct.
        """

        filepath = Path(path) if not isinstance(path, Path) else path
        log.debug("✨ Creating new Document from filename '%s'", filepath)

        stem = filepath.stem
        split = stem.split("_")
        album = filepath.parent.name
        if len(split) < 3 or album == "":
            raise TypeError(f"Cannot parse filename '{filepath}'")

        # Parse the datetime from the filename using dateutil
        try:
            timestamp_str = f"{split[1]} {split[2].replace('-', ':')}"
            timestamp = parse_datetime(timestamp_str)
        except (ParserError, OverflowError):
            raise TypeError(f"Cannot parse timestamp from filename '{filepath}'")

        # These paths need to be relative so we can make them portable
        json_path = Path(batch_name) / "json" / album / f"{stem}.json"
        text_path = Path(batch_name) / "text" / album / f"{stem}.txt"
        image_path = Path("img") / album / f"{stem}.webp"

        if not scan:
            return await cls.create(
                scan=await Scan.create(
                    stem=stem,
                    album=album,
                    album_index=int(split[0]),
                    title="_".join(split[3:]),
                    path=f"{image_path}",
                    url=f"{config.s3.url}/{image_path}",
                    thumb_url=f"{config.s3.url}/thumbs/{album}/{stem}.webp",
                    scanned_at=timestamp,
                    immediate=immediate,
                    session=session,
                ),
                batch_name=batch_name,
                json_path=f"{json_path}",
                json_url=f"{config.s3.url}/{json_path}",
                text_path=f"{text_path}",
                text_url=f"{config.s3.url}/{text_path}",
                immediate=immediate,
                session=session,
            )

        return await cls.create(
            scan=scan,
            batch_name=batch_name,
            json_path=f"{json_path}",
            json_url=f"{config.s3.url}/{json_path}",
            text_path=f"{text_path}",
            text_url=f"{config.s3.url}/{text_path}",
            immediate=immediate,
            session=session,
        )

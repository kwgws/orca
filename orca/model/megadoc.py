import logging
import os

import regex as re
from slugify import slugify
from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from orca import _config
from orca.model.base import (
    Base,
    CommonMixin,
    StatusMixin,
    create_uid,
    get_redis_client,
    utcnow,
)

log = logging.getLogger(__name__)
r = get_redis_client()


class Megadoc(Base, CommonMixin, StatusMixin):
    """A megadoc is text file containing the results of every document matching
    our search. This is the main thing we're here to produce.
    """

    uid = Column(String, primary_key=True)
    filetype = Column(String, nullable=False, default=".txt")
    filename = Column(String)
    path = Column(String)
    url = Column(String)
    search_uid = Column(String, ForeignKey("searches.uid"), nullable=False)
    search = relationship("Search", back_populates="megadocs")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # We need the ID to generate paths so we'll do it manually here
        self.uid = create_uid()

        # Generate the paths
        timestamp = re.sub(
            r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}).*",
            r"\1\2\3-\4\5\6",
            f"{utcnow().isoformat()}",
        )
        self.filename = f"{slugify(self.search.search_str)}_{timestamp}Z{self.filetype}"
        self.path = f"{_config.MEGADOC_PATH / self.filename}"
        if self.full_path.is_file():
            log.warning(f"File already exists, could be error: {self.full_path}")
        self.url = f"{_config.CDN_URL}/{self.path}"

        # Clear redis progress ticker
        r.hset(self.redis_key, "progress", 0)

    @property
    def full_path(self):
        """Returns the full canonical path as a pathlib object."""
        return _config.DATA_PATH / self.path

    @property
    def filesize(self):
        """Size of megadoc file in bytes. Returns 0 if no file."""
        try:
            return os.path.getsize(self.full_path)
        except OSError as e:
            log.warning(f"Error finding size of megadoc: {e}")
            return 0

    @property
    def progress(self):
        """Get current progress from redis if working."""
        if self.status == "PENDING":
            return 0.0
        if self.status in {"SENDING", "SUCCESS"}:
            return 100.0
        ticks = float(int(r.hget(self.redis_key, "progress")))
        return ticks / float(len(self.search.documents))

    def tick(self, n=1):
        """Increment redis progress ticker."""
        ticks = int(r.hget(self.redis_key, "progress"))
        r.hset(self.redis_key, "progress", ticks + n)

    def as_dict(self):
        rows = super().as_dict()
        for key in {"filename", "path", "search_uid"}:
            rows.pop(key)
        rows["filesize"] = self.filesize
        if self.status not in ["SENDING", "SUCCESS"]:
            rows["progress"] = self.progress
        return rows

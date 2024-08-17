import base64
import logging
import uuid
import zlib
from datetime import datetime, timezone

log = logging.getLogger(__name__)


def create_uid():
    """Create url-safe UID.

    We're using UIDs instead of sequential integers because of the archival
    nature of the project. We want to be able to reference everything in a
    stable way over a long period of time, even at the cost of performance.
    """
    uid_b64 = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b"=")
    return uid_b64.decode("ascii")


def create_crc(data):
    """Create an unsigned 8-byte hexadecimal checksum using CRC32."""
    if not data:
        log.warning("Tried to generate checksum for empty data")
        return 0
    checksum = zlib.crc32(data.encode()) & 0xFFFFFFFF
    return f"{checksum:08x}"


def utc_now():
    """Future-proofed replacement for deprecated `datetime.utcnow()`."""
    return datetime.now(timezone.utc)


def utc_old():
    """Returns standard, arbitrary 'old' date using timezone-aware format."""
    return datetime(1970, 1, 1, tzinfo=timezone.utc)

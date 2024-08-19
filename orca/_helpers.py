import base64
import logging
import uuid
import zlib
from datetime import datetime, timezone

import regex as re

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


def snake_to_camel(snake_str: str):
    """Convert Python-style snake case to JavaScript-style camel case."""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def export_dict(data: dict):
    """Convert Python-style snake case keys to JavaScript-style camel case."""
    if not data or not isinstance(data, dict):
        log.warning("No dictionary passed to export converter")
        return None

    def convert(value):
        if isinstance(value, dict):
            return export_dict(value)
        if isinstance(value, list):
            return [convert(item) for item in value]
        return value

    return {snake_to_camel(key): convert(value) for key, value in data.items()}


def camel_to_snake(camel_str: str):
    """Convert JavaScript-style camel case to Python-style snake case."""

    # Insert an underscore before a single uppercase letter that is either
    # preceded by a lowercase letter or followed by a lowercase letter
    snake_str = re.sub(r"(?<!^)(?<![A-Z])([A-Z])", r"_\1", camel_str)

    # Handle the case where a sequence of uppercase letters is followed by a
    # lowercase letter
    snake_str = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", snake_str)
    return snake_str.lower()


def import_dict(data: dict):
    """Convert JavaScript-style camel case keys to Python-style snake case."""
    if not data or not isinstance(data, dict):
        log.warning("No dictionary passed to import converter")
        return None
    return {camel_to_snake(key): value for key, value in data.items()}

"""Handy functions which aren't specifically tied to any one module.
"""

import base64
import os
import uuid
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, overload

import regex as re
from dateutil.parser import ParserError
from dateutil.parser import parse as _dtparse


def create_checksum(data: bytes | str) -> str:
    """Creates an unsigned 8-byte CRC32 checksum.

    This checksum is useful for verifying data integrity or for detecting
    changes in content.

    Args:
        data(bytes or str): Data to checksum. If a string is provided, it will
            be encoded to bytes before processing.

    Returns:
        CRC32 checksum as an 8-character hexadecimal string.
    """
    if isinstance(data, str):
        data = data.encode()
    checksum = zlib.crc32(data) & 0xFFFFFFFF
    return f"{checksum:08x}"


def create_guid() -> str:
    """Creates a URL-safe, 22-byte, base-64 GUID encoded GUID..

    We're using GUIDs instead of sequential integers because of the archival
    nature of the project. We want to be able to reference everything in a
    stable way over a long period of time, even at the cost of performance.

    Returns:
        A 22-character base-64 encoded GUID string.
    """
    guid_b64 = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b"=")
    return guid_b64.decode("ascii")


def do(n: int, n_max: int, batch_size: int) -> bool:
    """Determines if an action should be performed based on batch processing
    logic.

    Args:
        n (int): Current iteration number with zero-based index.
        n_max (int): Maximum number of iterations.
        batch_size (int): The size of each batch.

    Returns:
        `True` if the action should be performed, otherwise `False`.
    """
    return (n == 0) or ((n + 1) % batch_size == 0) or (n + 1 == n_max)


def dt_now() -> datetime:
    """Returns current date and time in UTC as a timezone-aware `datetime`
    object.

    Returns:
        Current date and time (UTC) as `datetime` object.
    """
    return datetime.now(timezone.utc)


def dt_old() -> datetime:
    """Returns standard, arbitrary 'old' date using timezone-aware format.

    Returns:
        January 1, 1970 (UTC) as `datetime` object.
    """
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


def filesize(filename: str | Path) -> int:
    """Returns the size of a file in bytes.

    Args:
        filename (str or Path): Path to the file.

    Returns:
        Size of the file in bytes, or 0 if the file cannot be accessed.
    """
    try:
        path = filename if isinstance(filename, Path) else Path(filename)
        path.touch()
        return os.path.getsize(path)
    except (FileNotFoundError, PermissionError):
        return 0


def parse_dt(data: str) -> datetime:
    """Parses a string into a timezone-aware datetime object.

    This function uses `dateutil.parser.parse()` for robust parsing. If the
    input string does not include timezone information, it defaults to UTC. If
    the string cannot be parsed, it falls back to January 1, 1970 (UTC).

    Args:
        data (str): The datetime string to parse.

    Returns:
        The parsed `datetime` object, or January 1, 1970 (UTC) on error.
    """
    try:
        dt = _dtparse(data)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    except (ParserError, OverflowError):
        return dt_old()


@overload
def deserialize(
    data: dict[str, Any], excl: set[str] | None = None, recursive=True, from_js=False
) -> dict[str, Any]: ...


@overload
def deserialize(
    data: list[Any], excl: set[str] | None = None, recursive=True, from_js=False
) -> list[Any]: ...


def deserialize(  # noqa: C901 (nested but straightforward conditionals)
    data: dict[str, Any] | list[Any],
    excl: set[str] | None = None,
    recursive=True,
    from_js=False,
) -> dict[str, Any] | list[Any]:
    """Converts values in a dictionary or list of dictionaries to native Python
    data objects based on their keys.

    - Keys ending in "_path" are converted to `pathlib.Path`.
    - Keys ending with "_at" are parsed as `datetime` objects.

    Parameters:
        data (dict or list): Dictionary or list to be deserialized.
        excl (set[str], optional): Set of keys to ignore.
        recursive (bool, optional): If `True`, recursively deserializes nested
            dictionaries and lists. Defaults to `True`.
        from_js (bool, optional): If `True`, converts keys to `snake_case` for
            import from a `camelCase` JavaScript environment. Defaults to
            `False`.

    Returns:
        Deserialized dictionary or list.
    """

    def camel_to_snake(camel_str: str) -> str:
        """Convert JavaScript-style camel case to Python-style snake case."""
        # Insert an underscore before a single uppercase letter that is either
        # preceded by a lowercase letter or followed by a lowercase letter
        snake_str = re.sub(r"(?<!^)(?<![A-Z])([A-Z])", r"_\1", camel_str)

        # Handle the case where a sequence of uppercase letters is followed by
        # a lowercase letter
        snake_str = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", snake_str)
        return snake_str.lower()

    if isinstance(data, dict):
        output = {}

        for k, item in data.items():
            key = camel_to_snake(k) if from_js else k
            if key in (excl or set()):
                continue

            # Convert path strings to pathlib objects
            if isinstance(item, str) and key.endswith("_path"):
                output[key] = Path(item)

            # Convert datetime strings to datetime objects
            elif isinstance(item, str) and key.endswith("_at"):
                output[key] = parse_dt(item)

            # Recurse on containers
            elif recursive and isinstance(item, (dict, list)):
                output[key] = deserialize(
                    item, excl=excl, recursive=recursive, from_js=from_js
                )

            else:
                output[key] = item

        return output

    elif isinstance(data, list):
        output = []
        for item in data:
            output.append(
                item
                if not isinstance(item, (dict, list))
                else deserialize(item, excl=excl, recursive=recursive, from_js=from_js)
            )
        return output


@overload
def serialize(
    data: dict[str, Any], excl: set[str] | None = None, recursive=True, to_js=False
) -> dict[str, Any]: ...


@overload
def serialize(
    data: list[Any], excl: set[str] | None = None, recursive=True, to_js=False
) -> list[Any]: ...


def serialize(  # noqa: C901 (nested but straightforward conditionals)
    data: dict[str, Any] | list[Any],
    excl: set[str] | None = None,
    recursive=True,
    to_js=False,
) -> dict[str, Any] | list[Any]:
    """Converts values in a dictionary or list of dictionaries to serializable
    values data objects for export or web handling based on their type.

    - `pathlib.Path` objects are converted to `str`.
    - `datetime` objects are converted to `str` via `.isoformat()`.

    Parameters:
        data (dict or list): Dictionary or list to be serialized.
        excl (set[str], optional): Set of keys to ignore.
        recursive (bool, optional): If `True`, recursively serializes nested
            dictionaries and lists. Defaults to `True`.
        to_js (bool, optional): If `True`, converts keys to `camelCase` for a
            JavaScript environment. Defaults to `False`.

    Returns:
        Serialized dictionary or list.
    """

    def snake_to_camel(snake_str: str) -> str:
        """Convert Python-style snake case to JavaScript-style camel case."""
        parts = snake_str.lower().split("_")
        return parts[0] + "".join(part.title() for part in parts[1:])

    if isinstance(data, dict):
        output = {}

        for k, item in data.items():
            if k in (excl or set()):
                continue
            key = snake_to_camel(k) if to_js else k

            if isinstance(item, Path):
                output[key] = str(item)

            elif isinstance(item, datetime):
                output[key] = (  # sub in tz-awareness if necessary
                    item
                    if item.tzinfo is not None
                    else item.replace(tzinfo=timezone.utc)
                ).isoformat()

            elif recursive and isinstance(item, (dict, list)):  # recurse
                output[key] = serialize(
                    item, excl=excl, recursive=recursive, to_js=to_js
                )

            else:
                output[key] = item

        return output

    elif isinstance(data, list):
        output = []
        for item in data:
            output.append(
                item
                if not isinstance(item, (dict, list))
                else serialize(item, excl=excl, recursive=recursive, to_js=to_js)
            )
        return output

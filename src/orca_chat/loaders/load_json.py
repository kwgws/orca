"""orca_chat/loaders/load_json.py"""

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path, *, not_exist_ok=True) -> dict[str, Any]:
    """Return deserialized JSON from file."""
    file_path = Path(path)
    if not file_path.exists() or file_path.stat().st_size == 0:
        if not_exist_ok:
            return {}
        else:
            raise FileNotFoundError(file_path)

    with file_path.open("rb") as f:
        data = json.load(f)

    if not data:
        return {}

    if not isinstance(data, dict):
        raise ValueError(f"JSON file {file_path} must contain dict, got {type(data).__name__}")

    return data

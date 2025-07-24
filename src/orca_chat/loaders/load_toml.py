"""orca_chat/loaders/load_toml.py"""

import os
import tomllib as toml
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import dotenv

dotenv.load_dotenv()


def load_toml(path: str | Path, *, expand_env=True) -> dict[str, Any]:
    """Read a TOML file, optionally expanding ``${ENV_VAR}`` tokens."""
    file_path = Path(path)
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise FileNotFoundError(file_path)

    with file_path.open("rb") as f:
        data = toml.load(f)

    if not data:
        raise ValueError(f"TOML file {file_path} is empty")

    if expand_env:
        return _expand_env_vars(data)
    return data


def to_namespace(d: dict) -> SimpleNamespace:
    """Convert mapping to nested :class:`SimpleNamespace`."""
    ns = SimpleNamespace()
    for key, val in d.items():
        if isinstance(val, dict):
            setattr(ns, key, to_namespace(val))
        else:
            setattr(ns, key, val)
    return ns


def validate(raw: Mapping[str, Any], *, keys: Sequence[str]) -> None:
    """Raise ``ValueError`` if any of ``keys`` are absent from ``raw``."""
    missing = [k for k in keys if k not in raw]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")


def _expand_env_vars(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars(i) for i in obj]
    if isinstance(obj, str):
        return os.path.expandvars(obj)
    return obj

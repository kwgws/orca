import os
import tomllib
from pathlib import Path
from typing import Any

import dotenv

_MODEL_CONFIG_PATH = Path(__file__).parent.parent / "config" / "models.toml"


def _expand(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _expand(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand(i) for i in obj]
    if isinstance(obj, str):
        return os.path.expandvars(obj)
    return obj


def load_models(extra_path: str | None = None) -> dict[str, Any]:
    with _MODEL_CONFIG_PATH.open("rb") as f:
        cfg = tomllib.load(f)

    if extra_path and Path(extra_path).exists():
        with Path(extra_path).open("rb") as f:
            cfg |= tomllib.load(f)

    dotenv.load_dotenv()
    return _expand(cfg)

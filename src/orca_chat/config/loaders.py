import os
import tomllib
from pathlib import Path
from typing import Any

import dotenv

__all__ = ["load_config", "load_prompt"]


def _expand(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _expand(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand(i) for i in obj]
    if isinstance(obj, str):
        return os.path.expandvars(obj)
    return obj


def load_config(name: str, extra_path: str | None = None) -> dict[str, Any]:
    base = Path(__file__).parent / f"{name}.toml"
    with base.open("rb") as f:
        cfg = tomllib.load(f)

    if extra_path and Path(extra_path).exists():
        with Path(extra_path).open("rb") as f:
            cfg |= tomllib.load(f)

    dotenv.load_dotenv()
    return _expand(cfg)


def load_prompt(name: str) -> str:
    base = Path(__file__).parent / "prompts" / f"{name}.md"
    with base.open("r") as f:
        prompt = f.read().strip()
    return prompt

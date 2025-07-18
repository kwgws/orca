"""orca_chat/config/load.py"""

import logging
import logging.config
import os
import tomllib as toml
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

import dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

dotenv.load_dotenv()

CFG_DIR = Path(__file__).parent
LOGGING_FILE = CFG_DIR / "logging.toml"
SKILLS_DIR = CFG_DIR / "skills"


@dataclass(slots=True, frozen=True)
class SkillConfig:
    node: str
    model: str
    base_url: str
    params: dict[str, Any]
    prompt: ChatPromptTemplate


@cache
def load_skill(name: str, path: str | Path = SKILLS_DIR) -> SkillConfig:
    """Load one skill TOML, validate, compile, and cache."""
    dir_path = Path(path).resolve()
    file_path = dir_path / f"{name}.toml"

    try:
        cfg = load_toml(file_path)
        _validate(cfg, keys=("model", "base_url", "messages"))

        return SkillConfig(
            node=cfg["node"].strip(),
            model=cfg["model"].strip(),
            base_url=cfg["base_url"].strip(),
            params=cfg.get("params", {}),
            prompt=_build_prompt(cfg["messages"]),
        )

    except (FileNotFoundError, ValueError, KeyError, toml.TOMLDecodeError) as e:
        raise ValueError(f"Error loading skill from {file_path}") from e


def _build_prompt(messages: Iterable[Mapping[str, str]]) -> ChatPromptTemplate:
    chain = []

    for msg in messages:
        _validate(msg, keys=("role", "template"))
        role = msg["role"].strip().lower()
        template = msg["template"].strip()

        if role != "placeholder":
            chain.append((role, template))
        else:
            chain.append(MessagesPlaceholder(template))

    return ChatPromptTemplate.from_messages(chain)


def _expand_env_vars(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars(i) for i in obj]
    if isinstance(obj, str):
        return os.path.expandvars(obj)
    return obj


def _validate(raw: Mapping[str, Any], *, keys: Sequence[str]) -> None:
    missing = [k for k in keys if k not in raw]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")


def load_toml(path: str | Path) -> dict[str, Any]:
    """Read a TOML file and expand any ${ENV_VAR} tokens."""
    with Path(path).open("rb") as f:
        cfg = toml.load(f)

    return _expand_env_vars(cfg)


@lru_cache(maxsize=1)
def load_logger(path: str | Path = LOGGING_FILE) -> logging.Logger:
    """Initialize the root logger from specified .TOML file."""
    log_config = load_toml(path)
    logging.config.dictConfig(log_config)
    return logging.getLogger()

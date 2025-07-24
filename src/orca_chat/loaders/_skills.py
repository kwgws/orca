"""orca_chat/loaders/_skills.py"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from langchain.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder

from .load_toml import load_toml, validate

SKILLS_DIR = Path(__file__).parent.parent / "config" / "skills"

RAGConfig = dict[str, Any]


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """Configuration for LLM-backed skills."""

    model: str
    base_url: str
    prompt: ChatPromptTemplate
    params: dict[str, Any] = field(default_factory=dict)


@cache
def load_skill(name: str, skills_dir: str | Path = SKILLS_DIR) -> LLMConfig | RAGConfig:
    """Load one skill configuration.

    Parameters
    ----------
    name
        Skill name matching ``<name>.toml``.
    skills_dir
        Directory containing ``<skill>.toml`` files. Defaults to the ``skills``
        folder in the ``config`` directory.
    """
    dir_path = Path(skills_dir).resolve()
    file_path = dir_path / f"{name}.toml"
    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    try:
        cfg = load_toml(file_path)
        validate(cfg, keys=("node_type",))
        node_type = cfg["node_type"].lower().strip()

        if node_type == "llm":
            validate(cfg, keys=("model", "base_url", "messages"))
            llm_cfg = LLMConfig(
                model=cfg["model"].strip(),
                base_url=cfg["base_url"].strip(),
                params=cfg.get("params", {}),
                prompt=_build_prompt(cfg["messages"]),
            )
            return llm_cfg

        if node_type == "rag":
            gen_cfg: RAGConfig = cfg.get("params", {})
            return gen_cfg

        raise KeyError(f"Bad node_type or not specified '{node_type}'")

    except (FileNotFoundError, ValueError, KeyError) as e:
        raise ValueError(f"Could not parse skill file {file_path}") from e


def _build_prompt(messages: Iterable[Mapping[str, str]]) -> ChatPromptTemplate:
    chain = []

    for msg in messages:
        validate(msg, keys=("role", "template"))
        role = msg["role"].strip().lower()
        template = msg["template"].strip()

        if role != "placeholder":
            chain.append((role, template))
        else:
            chain.append(MessagesPlaceholder(template))

    return ChatPromptTemplate.from_messages(chain)

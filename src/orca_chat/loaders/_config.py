"""orca_chat/interfaces/loaders/_config.py"""

from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

from .load_toml import load_toml, to_namespace

CONFIG_FILE = Path(__file__).parent.parent / "config" / "config.toml"

# ...
Config = SimpleNamespace


@lru_cache(maxsize=1)
def load_config(path: str | Path = CONFIG_FILE) -> Config:
    """..."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    cfg: Config = to_namespace(load_toml(file_path))
    return cfg

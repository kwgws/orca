"""orca_chat/loaders/_loggers.py"""

import logging
import logging.config
from functools import lru_cache
from pathlib import Path
from typing import Any

from .load_toml import load_toml

LOGGERS_FILE = Path(__file__).parent.parent / "config" / "loggers.toml"


@lru_cache(maxsize=1)
def load_logger(path: str | Path = LOGGERS_FILE) -> logging.Logger:
    """Initialize the root logger from a TOML file."""
    log_cfg = load_toml(path)

    # create log file directory/ies
    def _make_dirs(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "filename" and value and isinstance(value, str):
                    Path(value).parent.mkdir(parents=True, exist_ok=True)
                _make_dirs(value)

    _make_dirs(log_cfg)

    logging.config.dictConfig(log_cfg)
    return logging.getLogger()

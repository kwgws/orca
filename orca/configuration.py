"""
Configuration tools for app settings, SQLite database, and S3 bucket.

This module provides classes and functions for managing application settings,
including database configuration, S3 bucket integration, and loggers.

The configuration is loaded from a `.toml` file specified by the `CONFIG_FILE`
environment variable. If `CONFIG_FILE` is not set, the module defaults to
`orca.toml` in the current working directory.
"""

import logging
import logging.config
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .helpers import deserialize

_config_path = Path(os.getenv("CONFIG_FILE", "orca.toml"))
"""Path to the configuration file, defaults to '/.orca.toml'."""


@dataclass(frozen=True)
class DatabaseConfig:
    """Configuration for the SQLite database.

    This class holds settings required to connect to and interact with an
    SQLite database. It includes the path to the database file, the number of
    retries for database operations, and the batch size for processing rows per
    commit.

    Attributes:
        sql_path (Path): Path to the SQLite database file.
        retries (int, optional): Number of retry attempts for operations.
            Defaults to 3.
        batch_size (int, optional): Number of rows to process per commit.
            Defaults to 10000.
    """

    sql_path: Path = field()
    retries: int = field(default=3)
    batch_size: int = field(default=10000)

    @property
    def uri(self):
        """URI of SQLite db file"""
        return f"sqlite+aiosqlite:///{self.sql_path}"


@dataclass(frozen=True)
class S3Config:
    """Configuration for the S3 bucket.

    This class manages settings for connecting to an S3-compatible storage
    service, such as the endpoint, region, and access credentials.

    Attributes:
        url (str): Full public CDN URL for the S3 bucket.
        endpoint (str): Full URL for the S3 service endpoint.
        region (str): S3 region where the bucket is located.
        space (str): Name of the S3 bucket.
    """

    def __post_init__(self):
        if not self.access_key or not self.secret_key:
            raise ValueError("Could not retrieve S3 secrets from environment")

    url: str = field()
    endpoint: str = field()
    region: str = field()
    space: str = field()

    @property
    def access_key(self) -> str:
        """Access key for S3 authentication."""
        return os.getenv("S3_KEY", "")

    @property
    def secret_key(self) -> str:
        """Secret key for S3 authentication."""
        return os.getenv("S3_SECRET", "")


@dataclass(frozen=True)
class Config:
    """Main application configuration.

    This class encapsulates all the application settings, including database
    configuration, S3 bucket settings, and logging configuration.

    Attributes:
        version (str): Application version.
        client_url (str): Public URL of the web client.
        api_url (str): Public URL of the web API.
        s3 (S3Config): S3 bucket configuration object.
        db (DatabaseConfig): SQLite database configuration object.
        logger (dict[str, Any]): Logging configuration settings compatible with
            `dictConfig()`.
        app_name (str, optional): Name of the application. Defaults to "orca".
        root_path (Path, optional): Root path of the application. Defaults to
            the current working directory.
        batch_name (str, optional): Name of the current processing batch.
            Defaults to "00".
        megadoc_types (tuple, optional): Tuple of allowed megadoc file types.
            Defaults to ".txt" and ".docx".
    """

    version: str = field()
    client_url: str = field()
    api_url: str = field()
    s3: S3Config = field()
    db: DatabaseConfig = field()
    logger: dict[str, Any] = field()
    app_name: str = field(default="orca")
    root_path: Path = field(default=Path.cwd())
    batch_name: str = field(default="00")
    megadoc_types: tuple[str, ...] = field(default=(".txt", ".docx"))

    @property
    def data_path(self):
        """Gets the **absolute** path to the directory where data files are
        stored.
        """
        return self.root_path / "data"

    @property
    def index_path(self):
        """Get the **absolute** path to the directory where the Whoosh index is
        stored.
        """
        return self.data_path / self.batch_name / "index"

    @property
    def megadoc_path(self):
        """Get the **relative** path to the megadocs for the current data batch."""
        return Path(self.batch_name) / "megadocs"


_is_config_initialized = False
_config: Config
"""Global instance of the application configuration."""


def _load_config():
    """Load the `Config` object from the specified `.toml` file.

    This function reads configuration data from a `.toml` file, deserializes
    it into the appropriate Python objects, and returns a `Config` instance.
    It ensures that the configuration is only loaded once, subsequent calls
    will return the already loaded configuration.

    Returns:
    - Config: The loaded `Config` object.
    Raises:
        ValueError: If the `.toml` file is missing or if any critical
            configuration data (such as logging settings) is not provided.
    """
    global _is_config_initialized, _config
    if _is_config_initialized:
        return _config

    try:
        config_data = tomllib.loads(_config_path.read_text())

        # Extract and validate the logging configuration
        logger = config_data.pop("logging")
        if not logger:
            raise ValueError(f"No logging config provided in {_config_path}")

        # Deserialize remaining configuration data
        config_data = deserialize(config_data)
        config_data["logger"] = logger
        config_data["db"] = DatabaseConfig(**config_data.pop("database"))
        config_data["s3"] = S3Config(**config_data.pop("s3"))
        config_data.update(config_data.pop("app"))
        config = Config(**config_data)

        _is_config_initialized = True
        return config

    except Exception:
        raise ValueError(f"Could not load configuration from {_config_path}")


# Load the configuration and apply the logging settings immediately
config = _load_config()
logging.config.dictConfig(config.logger)

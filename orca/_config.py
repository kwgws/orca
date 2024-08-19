import logging
import logging.config
import os
import tomllib
from pathlib import Path
from typing import NamedTuple, Optional

from redis import StrictRedis

_config_path = Path(os.getenv("CONFIG_FILE", "orca.toml"))


def convert_paths_to_path(data):
    """Helper function to recursively convert paths to pathlib objects."""
    for key, value in data.items():
        if isinstance(value, dict):
            convert_paths_to_path(value)
        elif key.endswith("path"):
            data[key] = Path(value)
    return data


class DatabaseConfig(NamedTuple):
    sql_path: Path
    redis_path: Path
    retries: int = 10
    batch_size: int = 10000

    @property
    def uri(self):
        return f"sqlite:///{self.sql_path}"

    @property
    def redis(self):
        return StrictRedis(unix_socket_path=self.redis_path.as_posix())


class CDNConfig(NamedTuple):
    url: str
    endpoint: str
    region: str
    space: str
    access_key: str
    secret_key: str


class CeleryConfig(NamedTuple):
    broker_url: str
    result_backend: str
    imports: tuple[str] = ("orca.tasks",)
    result_extended: bool = True
    task_send_sent_event: bool = True
    task_track_started: bool = True
    worker_send_task_events: bool = True
    worker_cancel_long_running_tasks_on_connection_loss: bool = True
    worker_redirect_stdouts_level: str = "INFO"
    broker_connection_retry_on_startup: bool = True


class FlaskConfig(NamedTuple):
    secret_key: str
    session_redis: Optional[StrictRedis] = None
    session_type: str = "redis"
    session_key_prefix: str = "orca:session:"


class Config(NamedTuple):
    version: str
    client_url: str
    log_path: Path
    app_name: str = "orca"
    root_path: Path = Path.home()
    batch_name: str = 00
    megadoc_types: tuple[str] = (".txt", ".docx")
    db: Optional[DatabaseConfig] = None
    cdn: Optional[CDNConfig] = None
    celery: Optional[CeleryConfig] = None
    flask: Optional[FlaskConfig] = None

    @property
    def data_path(self):
        return self.root_path / "data"

    @property
    def index_path(self):
        return self.data_path / self.batch_name / "index"

    @property
    def megadoc_path(self):
        return Path(self.batch_name) / "megadocs"


# Open the configuration file
try:
    _values = tomllib.loads(_config_path.read_text())
    _values = convert_paths_to_path(_values)

    # Configure logging
    logging.config.dictConfig(_values.pop("logging"))

    # Populate remaining settings
    config = Config(
        db=DatabaseConfig(**_values.get("db")),
        cdn=CDNConfig(**_values.get("cdn")),
        celery=CeleryConfig(**_values.get("celery")),
        flask=FlaskConfig(**_values.get("flask")),
        **_values.get("app"),
    )

except Exception as e:
    raise EnvironmentError("Error loading configuration file") from e

import logging
import logging.handlers
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

# Validate critical parameters
load_dotenv()
for var in [
    "ORCA_CLIENT_URL",
    "ORCA_CDN_ACCESS_KEY",
    "ORCA_CDN_SECRET_KEY",
    "ORCA_CDN_ENDPOINT",
    "ORCA_CDN_URL",
]:
    if os.getenv(var) is None:
        raise EnvironmentError(f"Missing environment variable: {var}")


# App metadata
APP_NAME = "ORCA Document Query API"
APP_VERSION = "2024-08-08f"
CLIENT_URL = os.getenv("ORCA_CLIENT_URL").rstrip("/")

# Logging configuration
LOG_PATH: Path = Path(os.getenv("ORCA_LOG_PATH", "/var/log/orca"))
LOG_FILE: Path = LOG_PATH / "orca.log"
LOG_FORMAT: str = "%(asctime)s - %(levelname)s - %(message)s"
LOG_FORMAT_TASK: str = "%(asctime)s - %(levelname)s - %(task_name)s - %(message)s"
LOG_BACKUPS: int = 9

# Base paths
ROOT_PATH: Path = Path.home()
DATA_PATH: Path = Path(os.getenv("ORCA_DATA_PATH", f"{ROOT_PATH / 'data'}"))
DATA_PATH.mkdir(parents=True, exist_ok=True)
BATCH_NAME = os.getenv("ORCA_BATCH_NAME", "00")
BATCH_PATH: Path = Path(BATCH_NAME)
INDEX_PATH: Path = DATA_PATH / BATCH_PATH / "index"

# Database configuration
DATABASE_PATH: Path = ROOT_PATH / "orca.db"
DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
DATABASE_RETRIES: int = 10

# Redis configuration
REDIS_SOCKET: Path = Path(os.getenv("ORCA_REDIS_SOCKET"))
if not REDIS_SOCKET.exists():
    raise EnvironmentError(f"Cannot find redis socket at {REDIS_SOCKET}")

# Megadoc configuration
MEGADOC_FILETYPES: list[str] = [".txt", ".docx"]
MEGADOC_PATH: Path = BATCH_PATH / "megadocs"

# CDN configuraiton
CDN_ACCESS_KEY = os.getenv("ORCA_CDN_ACCESS_KEY")
CDN_SECRET_KEY = os.getenv("ORCA_CDN_SECRET_KEY")
CDN_ENDPOINT = os.getenv("ORCA_CDN_ENDPOINT").rstrip("/")
CDN_REGION = CDN_ENDPOINT.replace("https://", "").split(".")[0]
CDN_SPACE_NAME = "orca"
CDN_URL = os.getenv("ORCA_CDN_URL").rstrip("/")


# Celery configuration
class CeleryConfig:
    broker_url = f"redis+socket://{REDIS_SOCKET}"
    broker_connection_retry_on_startup: bool = True
    result_backend = f"redis+socket://{REDIS_SOCKET}"
    task_track_started = True
    worker_send_task_events = True
    task_send_sent_event = True
    result_extended = True
    worker_cancel_long_running_tasks_on_connection_loss = True


# Flask configuration
class FLASK:
    def __init__(self, redis_client):
        self.SECRET_KEY = os.getenv("ORCA_FLASK_KEY", str(uuid.uuid4()))
        self.SQLALCHEMY_DATABASE_URI = DATABASE_URI
        self.SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
        self.SESSION_TYPE = "redis"
        self.SESSION_REDIS: redis_client
        self.SESSION_PERMANENT: bool = False
        self.SESSION_USE_SIGNER: bool = True
        self.SESSION_KEY_PREFIX = "session:"
        self.DEBUG: bool = os.getenv("ORCA_FLASK_DEBUG", "False")


def setup_logger(name: str, level=logging.INFO):

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)

    # Create file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=(LOG_PATH / "orca.log").as_posix(),
        maxBytes=10 * 1024 * 1024,
        backupCount=LOG_BACKUPS,
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)

    return logger


# Initialize root logger
setup_logger("orca")

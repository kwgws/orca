import logging
import logging.config
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

# App metadata
APP_NAME = "orca"
APP_VERSION = "2024-08-08f"

# Initialize logging
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(name)s/%(levelname)s] %(message)s",
                "datefmt": "%Y-%d-%m %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "level": "WARNING",
                "class": "logging.StreamHandler",
                "formatter": "standard",
            },
            "file": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "/var/log/orca/orca.log",
                "maxBytes": 1024 * 1024 * 5,  # 5mb / log file
                "backupCount": 9,
                "formatter": "standard",
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": True,
            },
            "celery": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            # "celery.app.trace": {
            #    "handlers": ["console", "file"],
            #    "level": "INFO",
            #    "propagate": False,
            # },
        },
    }
)

# Validate critical parameters
load_dotenv()
for var in {
    "ORCA_CLIENT_URL",
    "ORCA_CDN_ACCESS_KEY",
    "ORCA_CDN_SECRET_KEY",
    "ORCA_CDN_ENDPOINT",
    "ORCA_CDN_URL",
}:
    if not os.getenv(var):
        raise EnvironmentError(f"Missing environment variable: {var}")


# Base paths
CLIENT_URL = os.getenv("ORCA_CLIENT_URL").rstrip("/")
ROOT_PATH = Path.home()
ROOT_PATH.mkdir(parents=True, exist_ok=True)
DATA_PATH = Path(os.getenv("ORCA_DATA_PATH", f"{ROOT_PATH / 'data'}"))
DATA_PATH.mkdir(parents=True, exist_ok=True)
BATCH_NAME = os.getenv("ORCA_BATCH_NAME", "00")
BATCH_PATH = Path(BATCH_NAME)
INDEX_PATH = DATA_PATH / BATCH_PATH / "index"

# Database configuration
DATABASE_PATH = ROOT_PATH / "orca.db"
DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
DATABASE_RETRIES = 10
DATABASE_BATCH_SIZE = 10000

# Redis configuration
if not (REDIS_SOCKET := Path(os.getenv("ORCA_REDIS_SOCKET"))).exists():
    raise EnvironmentError(f"Cannot find redis socket at {REDIS_SOCKET}")

# Megadoc configuration
MEGADOC_FILETYPES = [".txt", ".docx"]
MEGADOC_PATH = BATCH_PATH / "megadocs"

# CDN configuration
CDN_ACCESS_KEY = os.getenv("ORCA_CDN_ACCESS_KEY")
CDN_SECRET_KEY = os.getenv("ORCA_CDN_SECRET_KEY")
CDN_ENDPOINT = os.getenv("ORCA_CDN_ENDPOINT").rstrip("/")
CDN_REGION = CDN_ENDPOINT.replace("https://", "").split(".")[0]
CDN_SPACE_NAME = "orca"
CDN_URL = os.getenv("ORCA_CDN_URL").rstrip("/")


class CeleryConfig:
    broker_url = f"redis+socket://{REDIS_SOCKET}"
    broker_connection_retry_on_startup = True
    result_backend = f"redis+socket://{REDIS_SOCKET}"
    result_extended = True
    task_send_sent_event = True
    task_track_started = True
    worker_send_task_events = True
    worker_cancel_long_running_tasks_on_connection_loss = True
    worker_hijack_root_logger = False
    worker_redirect_stdouts_level = "INFO"


class FlaskConfig:
    SECRET_KEY = os.getenv("ORCA_FLASK_KEY", str(uuid.uuid4()))
    SESSION_TYPE = "redis"
    SESSION_KEY_PREFIX = "orca:session:"
    DEBUG = os.getenv("ORCA_FLASK_DEBUG", "false") == "true"

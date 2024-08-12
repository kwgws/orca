import logging
from functools import wraps

from celery import Celery

from orca_api import config
from orca_api.model import get_redis_client, get_session, handle_sql_errors

log = logging.getLogger("orca")

r = get_redis_client()


def with_session(func):
    """Decorator to acquire `SessionLocal` for Celery tasks.

    We need to override the `with_session()` from `orca_api.model` here so we
    can give each Celery task its own session for thread safety.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        with get_session() as session:
            kwargs["session"] = session
            return handle_sql_errors(func, *args, **kwargs)

    return wrapper


# Define Celery app; use configuration from orca_api.config
celery = Celery(__name__, config_source=config.CeleryConfig)

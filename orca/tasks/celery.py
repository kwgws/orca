from celery import Celery

from orca import _config

celery = Celery(_config.APP_NAME)
celery.config_from_object(_config.CeleryConfig)
celery.autodiscover_tasks(["orca.tasks"])

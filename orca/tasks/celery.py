from celery import Celery

from orca import config

celery = Celery(config.APP_NAME)
celery.config_from_object(config.CeleryConfig)
celery.autodiscover_tasks(["orca.tasks"])

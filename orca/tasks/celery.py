from celery import Celery

from orca import config

celery = Celery("orca")
celery.config_from_object(config.CeleryConfig)
celery.autodiscover_tasks(["orca.tasks"])

from celery import Celery

from orca import config

celery = Celery(config.app_name, config_source=config.celery)

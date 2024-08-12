from .controller import celery
from .load import start_load_documents  # noqa: F401

celery.autodiscover_tasks(
    [
        "orca_api.tasks.load",
        "orca_api.tasks.export",
        "orca_api.tasks.search",
    ]
)

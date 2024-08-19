import logging
from pathlib import Path

from celery import chain, chord, group

from orca import config
from orca._helpers import export_dict
from orca.model import Corpus, create_tables, with_session
from orca.tasks import celery  # noqa: F401
from orca.tasks.exporters import create_megadoc, upload_megadoc
from orca.tasks.loaders import index_documents, load_documents
from orca.tasks.searchers import run_search

log = logging.getLogger(__name__)


def reset_db():
    """Reset database, create metadata.

    This needs to be run at least once before anything else happens.
    """
    log.info(f"Deleting database file: {config.db.path}")
    config.db.path.unlink()
    log.info("Creating database and setting up table metadata")
    create_tables()
    log.info("Reset complete")


def start_load(path):
    """Load documents from path into the database.

    Each document needs to be in an album subdirectory and named according to
    the schema laid out in `Image.create_from_file()`.

    We start a Redis chord with one `load_documents()` task per subdirectory,
    then finish by creating a `Corpus` snapshot and building a Whoosh index
    with `index_documents()`.
    """

    if not (path := Path(path)).is_dir():
        raise IOError(f"Bad path: {path}")
    if not (subdirs := [p for p in path.iterdir() if p.is_dir()]):
        raise IOError(f"No albums in path: {path}")
    return chord([load_documents.s(str(p)) for p in subdirs])(
        chain(index_documents.s())
    )


@with_session
def get_overview(session=None):
    data = {
        "api_version": config.version,
        "corpus": Corpus.get_latest(session=session).as_dict(),
    }
    return export_dict(data)


def start_search(search_str):
    """ """
    megadoc_tasks = group(
        chain(create_megadoc.s(filetype), upload_megadoc.s())
        for filetype in config.megadoc_types
    )
    return chain(run_search.s(search_str), megadoc_tasks).apply_async()

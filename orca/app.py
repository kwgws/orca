import logging
from pathlib import Path

import click
from celery import chain, chord, group

from orca import config
from orca.model import create_tables, get_redis_client
from orca.tasks.celery import celery  # noqa: F401
from orca.tasks.load import index_documents, load_documents, reset_lock
from orca.tasks.search import create_megadoc, run_search, upload_megadoc

log = logging.getLogger("orca")
r = get_redis_client()


@click.group()
def cli():
    """Command line interface for the application."""
    pass


@cli.command
def reset():
    """Reset database, create metadata.

    This needs to be run at least once before anything else happens.
    """
    click.echo(f"Deleting databsae at {config.DATABASE_PATH}")
    config.DATABASE_PATH.unlink()
    click.echo(f"Creating database and metadata at {config.DATABASE_PATH}")
    create_tables()
    click.echo("Ok!")


@cli.command
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
)
def load(path):
    """Load documents from path into the database.

    Each document needs to be in an album subdirectory and named according to
    the schema laid out in `Image.create_from_file()`.

    We start a Redis chord with one `load_documents()` task per subdirectory,
    then finish by creating a `Corpus` snapshot and building a Whoosh index
    with `index_documents()`.
    """

    if r.hget("orca:flags", "loading") == b"1":
        raise RuntimeError("Tried loading documents but process already running")

    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_dir():
        raise IOError(f"Bad path: {path}")

    subdirs = [p for p in path.iterdir() if p.is_dir()]
    if not subdirs:
        raise IOError(f"No albums in path: {path}")

    r.hset("orca:flags", "loading", int(True))
    load_tasks = [load_documents.s(p.as_posix()) for p in subdirs]
    result = chord(load_tasks)(index_documents.s()).then(reset_lock.s())
    return result


@cli.command
@click.argument("search_str")
def search(search_str):
    log.info(f"Starting search for `{search_str}`")

    megadoc_tasks = group(
        chain(create_megadoc.s(filetype), upload_megadoc.s())
        for filetype in config.MEGADOC_FILETYPES
    )
    result = chain(run_search.s(search_str), megadoc_tasks).apply_async()
    return result

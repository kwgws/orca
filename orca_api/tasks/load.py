import logging
from pathlib import Path

from celery import chord
from natsort import natsorted
from unidecode import unidecode
from whoosh import index
from whoosh.fields import ID, TEXT, Schema
from whoosh.writing import AsyncWriter

from orca_api import config
from orca_api.model import Corpus, Document, Image, get_redis_client

from .controller import celery, with_session

log = logging.getLogger("orca")
r = get_redis_client()


def start_load_documents(path):
    """Load documents from path into the database.

    Each document needs to be in an album subdirectory and named according to
    the schema laid out in `Image.create_from_file()`.

    We start a Redis chord with one `load_documents()` task per subdirectory,
    then finish by creating a `Corpus` snapshot and building a Whoosh index
    with `index_documents()`.
    """

    if r.hget("orca:flags", "loading") == b"1":
        log.warning("Load documents is already flagged as running")
        # raise RuntimeError("Tried loading documents but process already running")

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


@celery.task(bind=True)
@with_session
def load_documents(self, path: str, session=None):
    """Load document metadata from a set of files.

    These files should be named and arranged according to the schema laid out
    in `Image.create_from_file()`
    """

    # Load list of file; sort, count
    path = Path(path)
    files = natsorted(path.glob("*.json"))
    total = len(files)

    for i, file in enumerate(files):
        # Commit & log every n files, making sure to always hit the last file,
        # otherwise just add the file to the batch
        if i == 0 or (i + 1) % 1000 == 0 or i + 1 == total:
            log.info(f"Loading {i + 1}/{total} from {path}")
            Image.create_from_file(file, session=session)
        else:
            Image.create_from_file(file, batch_only=True, session=session)


@celery.task(bind=True)
@with_session
def index_documents(self, _, session=None):
    """Index documents for full-text search using Whoosh.

    We use Whoosh because it gives us access to some special fuzzy text stuff.
    Nb this should only be run inside a single thread.
    """

    log.info("Building corpus snapshot")
    documents = Document.get_all(session=session)
    total = len(documents)
    Corpus.create(session=session)

    if any(config.INDEX_PATH.iterdir()):
        log.info("Previous index found, deleting")

        def rmdir(path: Path):
            for item in path.iterdir():
                if item.is_dir():
                    rmdir(item)
                else:
                    item.unlink()
            path.rmdir()

        rmdir(config.INDEX_PATH)
        config.INDEX_PATH.mkdir()

    schema = Schema(
        id=ID(stored=True, unique=True),
        content=TEXT(stored=True),
    )
    ix = index.create_in(config.INDEX_PATH, schema)
    writer = AsyncWriter(ix)

    for i, doc in enumerate(documents):
        if i == 0 or (i + 1) % 10000 == 0 or i + 1 == total:
            log.info(f"Indexing {i + 1}/{total} documents to {config.INDEX_PATH}")

        text_path = config.DATA_PATH / doc.text_path
        try:
            with text_path.open() as f:
                content = unidecode(f.read().strip())
            writer.add_document(id=doc.id, content=content)

        except IOError as e:
            log.warning(f"Error parsing {text_path}: {e}")

    log.info(f"Finalizing index at {config.INDEX_PATH}, this could take some time")
    writer.commit()
    log.info("Indexing complete!")


@celery.task
def reset_lock(self):
    r.hset("orca:flags", "loading", int(False))

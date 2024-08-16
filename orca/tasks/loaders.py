import logging
from pathlib import Path

from natsort import natsorted
from unidecode import unidecode
from whoosh import index
from whoosh.fields import ID, TEXT, Schema
from whoosh.writing import AsyncWriter

from orca import _config
from orca.model import Corpus, Document, Image, get_redis_client, with_session
from orca.tasks.celery import celery

log = logging.getLogger(_config.APP_NAME)
r = get_redis_client()


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
    log.info(f"Loading {total} documents from {path}")

    for i, file in enumerate(files):
        # Commit & log every n files, making sure to always hit the last file,
        # otherwise just add the file to the batch
        if (i + 1) % _config.DATABASE_BATCH_SIZE == 0 or i + 1 == total:
            log.info(f"Loading documents ({i + 1}/{total})")
            Image.create_from_file(file, session=session)
        else:
            Image.create_from_file(file, batch_only=True, session=session)

    log.info(f"Done loading documents from {path}")


@celery.task(bind=True)
@with_session
def index_documents(self, _, session=None):
    """Index documents for full-text search using Whoosh.

    We use Whoosh because it gives us access to some special fuzzy text stuff.
    Nb this should only be run inside a single thread.
    """

    documents = Document.get_all(session=session)
    total = len(documents)
    log.info(f"Indexing {total} documents to {_config.INDEX_PATH}")

    Corpus.create(session=session)

    if any(_config.INDEX_PATH.iterdir()):
        log.info(f"Previous index found at {_config.INDEX_PATH}, resetting")

        def rmdir(path: Path):
            for item in path.iterdir():
                if item.is_dir():
                    rmdir(item)
                else:
                    item.unlink()
            path.rmdir()

        rmdir(_config.INDEX_PATH)
        _config.INDEX_PATH.mkdir()

    schema = Schema(
        id=ID(stored=True, unique=True),
        content=TEXT(stored=True),
    )
    ix = index.create_in(_config.INDEX_PATH, schema)
    writer = AsyncWriter(ix)

    for i, doc in enumerate(documents):
        if (i + 1) % _config.DATABASE_BATCH_SIZE == 0 or i + 1 == total:
            log.info(f"Indexing documents ({i + 1}/{total})")

        text_path = _config.DATA_PATH / doc.text_path
        try:
            with text_path.open() as f:
                content = unidecode(f.read().strip())
            writer.add_document(id=doc.id, content=content)

        except IOError as e:
            log.warning(f"Error parsing {text_path}: {e}")

    log.info(f"Finalizing index at {_config.INDEX_PATH}, this could take some time")
    writer.commit()
    log.info("Done indexing")

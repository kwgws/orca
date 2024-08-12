import logging
from pathlib import Path

from natsort import natsorted
from unidecode import unidecode
from whoosh import index
from whoosh.fields import ID, TEXT, Schema
from whoosh.writing import AsyncWriter

from orca import config
from orca.model import Corpus, Document, Image, get_redis_client, with_session
from orca.tasks.celery import celery

log = logging.getLogger(config.APP_NAME)
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
        if (i + 1) % config.DATABASE_BATCH_SIZE == 0 or i + 1 == total:
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

    documents = Document.get_all(session=session)
    total = len(documents)
    log.info(f"Indexing {total} documents to {config.INDEX_PATH}")

    Corpus.create(session=session)

    if any(config.INDEX_PATH.iterdir()):
        log.info(f"Previous index found at {config.INDEX_PATH}, resetting")

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
        if (i + 1) % config.DATABASE_BATCH_SIZE == 0 or i + 1 == total:
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

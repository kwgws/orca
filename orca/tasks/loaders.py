import logging
import shutil
from pathlib import Path

import whoosh
import whoosh.fields
import whoosh.writing
from natsort import natsorted
from unidecode import unidecode

from orca import config
from orca.model import Corpus, Document, Image, with_session
from orca.tasks import celery

log = logging.getLogger(__name__)


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
        if (i + 1) % config.db.batch_size == 0 or i + 1 == total:
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
    log.info(f"Indexing {total} documents to {config.index_path}")

    Corpus.create(session=session)

    if any(config.index_path.iterdir()):
        log.info(f"Previous index found at {config.index_path}, resetting")
        shutil.rmtree(config.index_path)
        config.index_path.mkdir()

    schema = whoosh.fields.Schema(
        uid=whoosh.fields.ID(stored=True, unique=True),
        content=whoosh.fields.TEXT(stored=True),
    )
    ix = whoosh.index.create_in(config.index_path, schema)
    writer = whoosh.writing.AsyncWriter(ix)

    for i, doc in enumerate(documents):
        if (i + 1) % config.db.batch_size == 0 or i + 1 == total:
            log.info(f"Indexing documents ({i + 1}/{total})")

        text_path = config.data_path / doc.text_path
        try:
            with text_path.open() as f:
                content = unidecode(f.read().strip())
            writer.add_document(uid=doc.uid, content=content)

        except IOError as e:
            log.warning(f"Error parsing {text_path}: {e}")

    log.info(f"Finalizing index at {config.index_path}, this could take some time")
    writer.commit()
    log.info("Done indexing")

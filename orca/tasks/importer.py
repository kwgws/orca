"""
Module for importing documents and managing search indexes.

This module provides asynchronous functions for importing JSON documents into a
database and creating a search index using Whoosh. The imported documents are
processed in batches, and the search index is stored on disk, allowing for
efficient retrieval of document content.
"""

import asyncio
import logging
import shutil
from pathlib import Path

from natsort import natsorted
from sqlalchemy.ext.asyncio import AsyncSession
from whoosh.fields import ID, TEXT, Schema
from whoosh.index import FileIndex, create_in
from whoosh.writing import AsyncWriter

from orca import config
from orca.helpers import do
from orca.model import Corpus, Document, with_async_session

log = logging.getLogger(__name__)


@with_async_session
async def import_documents(
    data: Path | list[Path],
    *,
    batch_name: str = config.batch_name,
    session: AsyncSession,
) -> None:
    """
    Imports a list of files or files from a specified directory.

    This function loads JSON files from a list of paths or from the specified
    directory and creates corresponding `Document` entries in the database. The
    process is batched according to the configuration settings.

    Args:
        data (Path or list[Path]): List of individual file paths or path to a
            directory containing JSON files.
        batch_name (str, optional): Batch name, used to construct paths. This
            is usually provided by `config.data_path` but can be overridden
            here for edge cases or testing.
        session (AsyncSession, optional): An active asynchronous database
            session. If not provided, the method will create and manage its own
            session.
    """
    files = await asyncio.to_thread(
        natsorted,
        data.rglob("**/*.json") if isinstance(data, Path) else data,
    )
    file_count = len(files)

    for i, file in enumerate(files):
        if do_batch := do(i, file_count, config.db.batch_size):
            log.info("⏳ Importing documents (%d/%d)", i + 1, file_count)
        else:
            log.debug("⏳ Importing documents (%d/%d)", i + 1, file_count)
        await Document.create_from_file(
            path=file,
            scan=None,
            immediate=do_batch,
            batch_name=batch_name,
            session=session,
        )
    log.info("🌸 Done importing documents")


def _create_new_index(path: Path) -> FileIndex:
    """Creates a new Whoosh search index.

    This function initializes a new search index at the specified path. If an
    existing index is found, it will be deleted and replaced.

    Args:
        path (Path): The directory where the index will be stored.

    Returns:
        A Whoosh `FileIndex` object representing the new search index.
    """
    if path.is_dir() and any(path.iterdir()):
        log.info("🚧 Previous index found, resetting")
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    schema = Schema(
        guid=ID(sortable=True, stored=True, unique=True),
        content=TEXT(stored=True),
    )
    return create_in(path, schema)


@with_async_session
async def create_index(
    *,
    data_path: Path = config.data_path,
    index_path: Path = config.index_path,
    session: AsyncSession,
) -> None:
    """Creates a new search index for all `Document`s in the database.

    This function retrieves all `Document`s from the database, creates a new
    search index, and populates it with the `Document`s' contents.

    Args:
        data_path (Path, optional): Base data path where metadata files are
            stored. This is usually provided by `config.data_path` but can be
            overridden here for edge cases or testing.
        index_path (Path, optional): The path where the search index will be
            stored. This is usually provided by `config.index_path` but can be
            overridden here for edge cases or testing.
        session (AsyncSession, optional): An active asynchronous database
            session. If not provided, the method will create and manage its own
            session.
    """
    documents: list[Document] = await Document.get_all(session=session)
    document_count = len(documents)

    await Corpus.create(data_path=data_path, session=session)
    index = await asyncio.to_thread(_create_new_index, index_path)
    writer = AsyncWriter(index)

    for i, document in enumerate(documents):
        if do(i, document_count, config.db.batch_size):
            log.info("⏳ Indexing documents (%d/%d)", i + 1, document_count)
        else:
            log.debug("⏳ Indexing documents (%d/%d)", i + 1, document_count)
        writer.add_document(
            guid=document.guid,
            content=document.get_text(data_path=data_path),
        )

    log.info("⏳ Finalizing search index, this may take some time")
    await asyncio.to_thread(writer.commit)
    log.info("🌸 Done creating search index")

"""
Module for core API functions.

This module provides the core asynchronous functions to handle initialization
of the Orca SQL database, the import of albums into the system, document search
and megadoc creation, and running a debug server for testing purposes.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from natsort import natsorted
from sqlalchemy.ext.asyncio import AsyncSession

from . import config
from .helpers import create_checksum
from .model import (
    Base,
    Corpus,
    Search,
    db_lock,
    get_async_engine,
    init_async_engine,
    with_async_session,
)
from .tasks import (
    create_index,
    create_megadoc,
    create_search,
    import_documents,
    upload_megadoc,
)

log = logging.getLogger("orca")


async def init_database(
    uri: str = config.db.uri, path: Path = config.db.sql_path
) -> None:
    """Initialize the SQL database.

    This function sets up the SQL database by creating the necessary schema. If
    a database file already exists, it will be deleted and replaced with a
    fresh instance. The database file's permissions are adjusted for security.

    Args:
        uri (str): The database connection URI, defaulting to the value in the
            configuration.
        path (Path): The path where the SQL file should be created, defaulting
            to the value in the configuration.
    """
    async with db_lock:
        log.info(
            "🗄️ Creating new SQL database file at %s",
            path,
        )
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.unlink, missing_ok=True)

        log.info("🗄️ Initializing database at %s", uri)
        await init_async_engine(uri)
        engine = get_async_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # await asyncio.to_thread(path.chmod, 0o660)  # just in case


@with_async_session
async def import_albums(
    data_path: Path = config.data_path,
    batch_name: str = config.batch_name,
    index_path: Path = config.index_path,
    *,
    session: AsyncSession,
) -> None:
    """Import albums and documents into the system.

    This function scans the configured batch folder, imports the albums found
    within, and indexes the documents. The albums are sorted naturally using
    the natsort library to ensure proper order. If any errors are encountered,
    they are logged.

    Args:
        data_path (Path, optional): Base data path where metadata files are
            stored. This is usually provided by `config.data_path` but can be
            overridden here for edge cases or testing.
        batch_name (str): The name of the album batch to import.
        index_path (Path, optional): The path where the search index is stored.
            This is usually provided by `config.index_path` but can be
            overridden here for edge cases or testing.
        session (AsyncSession, optional): An active asynchronous database
            session. If not provided, the method will create and manage its own
            session.
    """
    batch_path = data_path / batch_name
    if not await asyncio.to_thread(batch_path.is_dir):
        log.error("💣 Error importing albums: Bad batch path %s", batch_path)
        return

    albums = await asyncio.to_thread(
        natsorted, [p for p in batch_path.iterdir() if p.is_dir()]
    )
    if len(albums) < 1:
        log.error("💣 Error importing albums: No albums in batch path %s", batch_path)
        return

    try:
        log.info("📚 Importing documents from %d albums in %s", len(albums), batch_path)
        await import_documents(batch_path, batch_name=batch_name, session=session)
        await create_index(data_path=data_path, index_path=index_path, session=session)
    except (RuntimeError, TypeError, ValueError):
        log.exception("💣 Error importing albums")
        return


@with_async_session
async def search_to_megadocs(
    search_str: str,
    data_path: Path = config.data_path,
    index_path: Path = config.index_path,
    megadoc_types: tuple[str, ...] = config.megadoc_types,
    *,
    session: AsyncSession,
) -> None:
    """Perform a search and create megadocs from the results.

    This function performs a search based on the provided search string, and
    for each megadoc type specified, it creates a megadoc and uploads it. The
    results are filtered and returned as a set of files in the configured data
    path.

    Args:
        search_str (str): The string used to perform the search.
        data_path (Path, optional): Base data path where metadata files are
            stored. This is usually provided by `config.data_path` but can be
            overridden here for edge cases or testing.
        index_path (Path, optional): The path where the search index is stored.
            This is usually provided by `config.index_path` but can be
            overridden here for edge cases or testing.
        megadoc_types (tuple[str, ...]): A tuple of file types for megadoc
            creation.
        session (AsyncSession, optional): An active asynchronous database
            session. If not provided, the method will create and manage its own
            session.
    """
    log.info("🔦 Starting search for '%s'", search_str)
    try:
        search: Search = await create_search(
            search_str, index_path=index_path, session=session
        )
    except ValueError:
        log.exception("💣 Error starting search")
        return
    except (RuntimeError, TypeError):
        log.exception("💣 Error running search")
        return

    log.info("✨ Creating megadocs for Search '%s' <%s>", search_str, search.guid)
    for filetype in megadoc_types:
        try:
            megadoc = await create_megadoc(
                filetype, search, data_path=data_path, session=session
            )
            await upload_megadoc(megadoc, data_path=data_path, session=session)
        except RuntimeError:
            log.exception("💣 Error creating megadoc")
            return


@with_async_session
async def export_corpus(session: AsyncSession) -> dict[str, Any]:
    corpus = await Corpus.get_latest(session=session)
    data = {
        "apiVersion": config.version,
        "corpus": corpus.as_dict(to_js=True) if corpus else {},
    }
    data["checksum"] = create_checksum(json.dumps(data, sort_keys=True))
    return data


@with_async_session
async def export_search(search_guid: str, *, session: AsyncSession) -> dict[str, Any]:
    search = await Search.get(search_guid, session=session)
    return search.as_dict(to_js=True) if search else {}


@with_async_session
async def delete_search(search_guid: str, *, session: AsyncSession) -> bool:
    if not (search := await Search.get(search_guid, session=session)):
        return False
    search.delete(session=session)
    return True

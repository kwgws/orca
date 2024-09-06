"""
Module for searching documents.

This module provides asynchronous functions for searching through the document
corpus and collecting results.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from whoosh.index import open_dir
from whoosh.qparser import FuzzyTermPlugin, QueryParser

from orca import config
from orca.model import Corpus, Document, Search, with_async_session

log = logging.getLogger(__name__)


def _run_whoosh_query(
    search_str: str, index_path: Path = config.index_path
) -> list[dict[str, Any]]:
    """Executes a search query using Whoosh.

    Args:
        search_str (str): The search query string.
        index_path (Path, optional): The path where the search index is stored.
            This is usually provided by `config.index_path` but can be
            overridden here for edge cases or testing.

    Returns:
        Results of the query as dictionary objects.
    """
    ix = open_dir(str(index_path))
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema)
        parser.add_plugin(FuzzyTermPlugin())
        results = [
            r.fields() for r in searcher.search(parser.parse(search_str), limit=None)
        ]
    return results


@with_async_session
async def create_search(
    search_str: str,
    *,
    index_path: Path = config.index_path,
    session: AsyncSession,
) -> Search:
    """Executes a search query against the latest `Corpus`.

    This function creates, persists, and returns a `Search` object containing
    the results of a given query string.

    Args:
        search_str (str): The search query string.
        index_path (Path, optional): The path where the search index is stored.
            This is usually provided by `config.index_path` but can be
            overridden here for edge cases or testing.
        session (AsyncSession, optional): An active asynchronous database
            session. If not provided, the method will create and manage its own
            session.

    Returns:
        The `Search` object containing the results of the query.

    Raises:
        ValueError: Search string is empty or no `Corpus` available.
        LookupError: `Document` referenced in the search results cannot be
            found in the database.
    """
    if len(search_str) < 3:
        raise ValueError(f"Invalid search string '{search_str}'")
    if not (corpus := await Corpus.get_latest(session=session)):
        raise ValueError("No Corpus available")

    search: Search = await Search.create(search_str, corpus, session=session)

    for result in await asyncio.to_thread(_run_whoosh_query, search_str, index_path):
        guid = result["guid"]

        if not (document := await Document.get(guid, session=session)):
            raise LookupError(
                f"Document <{guid}> referenced in index does not exist in database, "
                "index out of sync with database and likely needs to be rebuilt"
            )
        if document in await search.awaitable_attrs.documents:
            log.warning(
                "🚧 Tried adding duplicate Document <%s> to Search '%s' <%s>",
                guid,
                search_str,
                search.guid,
            )
            continue

        if not search.status == "STARTED":
            await search.set_status("STARTED", session=session)
        await search.add_document(document, session=session)

    log.info(
        "🌸 Finished Search '%s' <%s> with %d results",
        search_str,
        search.guid,
        search.document_count,
    )
    await search.set_status("SUCCESS", session=session)
    return search

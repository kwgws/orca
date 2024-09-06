import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from orca.model import Corpus, Document, Megadoc, Scan, Search


@pytest.mark.asyncio
async def test_get_session(session):
    assert isinstance(session, AsyncSession)
    assert session.is_active


@pytest.mark.asyncio
async def test_create_corpus(session):
    assert isinstance(session, AsyncSession)

    path = "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json"
    document = await Document.create_from_file(path=path, scan=None, session=session)
    scan = document.scan

    await session.refresh(scan)
    assert isinstance(scan, Scan)
    await session.refresh(document)
    assert isinstance(document, Document)

    corpus = await Corpus.create(session=session)
    await session.refresh(corpus)
    assert isinstance(corpus, Corpus)
    assert document in await corpus.awaitable_attrs.documents
    assert corpus.document_count == 1


@pytest.mark.asyncio
async def test_create_search(session):
    assert isinstance(session, AsyncSession)

    path = "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json"
    document = await Document.create_from_file(path=path, scan=None, session=session)
    scan = document.scan

    await session.refresh(scan)
    assert isinstance(scan, Scan)
    await session.refresh(document)
    assert isinstance(document, Document)

    corpus = await Corpus.create(session=session)
    await session.refresh(corpus)
    assert isinstance(corpus, Corpus)

    search = await Search.create("test_search", corpus, session=session)
    await session.refresh(search)
    assert isinstance(search, Search)


@pytest.mark.asyncio
async def test_set_invalid_status(session):
    assert isinstance(session, AsyncSession)

    path = "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json"
    document = await Document.create_from_file(path=path, scan=None, session=session)
    scan = document.scan

    await session.refresh(scan)
    assert isinstance(scan, Scan)
    await session.refresh(document)
    assert isinstance(document, Document)

    corpus = await Corpus.create(session=session)
    await session.refresh(corpus)
    assert isinstance(corpus, Corpus)

    search = await Search.create("test_search", corpus, session=session)
    await session.refresh(search)
    assert isinstance(search, Search)

    with pytest.raises(ValueError):
        await search.set_status("INVALID", session=session)


@pytest.mark.asyncio
async def test_add_document_to_search(session):
    assert isinstance(session, AsyncSession)

    path = "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json"
    document = await Document.create_from_file(path=path, scan=None, session=session)
    scan = document.scan

    await session.refresh(scan)
    assert isinstance(scan, Scan)
    await session.refresh(document)
    assert isinstance(document, Document)

    corpus = await Corpus.create(session=session)
    await session.refresh(corpus)
    assert isinstance(corpus, Corpus)

    search = await Search.create("test_search", corpus, session=session)
    await session.refresh(search)
    assert isinstance(search, Search)
    assert search.document_count == 0

    await search.add_document(document, session=session)
    await session.refresh(search)
    assert search.document_count == 1
    assert document in await search.awaitable_attrs.documents


@pytest.mark.asyncio
async def test_add_megadoc_to_search(session):
    assert isinstance(session, AsyncSession)

    path = "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json"
    document = await Document.create_from_file(path=path, scan=None, session=session)
    scan = document.scan

    assert isinstance(scan, Scan)
    assert isinstance(document, Document)

    corpus = await Corpus.create(session=session)
    assert isinstance(corpus, Corpus)

    search = await Search.create("test_search", corpus, session=session)
    assert isinstance(search, Search)

    megadoc = await search.add_megadoc(".txt", session=session)
    assert isinstance(megadoc, Megadoc)
    assert megadoc.search_guid == search.guid
    assert megadoc in search.megadocs
    await session.refresh(megadoc)
    assert megadoc.filename.startswith("test-search")

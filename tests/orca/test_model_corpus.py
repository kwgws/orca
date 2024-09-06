import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from orca.model import Corpus, Document, Scan


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

    assert isinstance(scan, Scan)
    assert isinstance(document, Document)

    corpus = await Corpus.create(session=session)
    assert isinstance(corpus, Corpus)
    assert document in await corpus.awaitable_attrs.documents
    assert corpus.document_count == 1


@pytest.mark.asyncio
async def test_get_corpus(session):
    assert isinstance(session, AsyncSession)

    path = "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json"
    document = await Document.create_from_file(path=path, scan=None, session=session)
    scan = document.scan

    assert isinstance(scan, Scan)
    assert isinstance(document, Document)

    corpus = await Corpus.create(session=session)
    assert isinstance(corpus, Corpus)

    the_corpus = await Corpus.get_latest(session=session)
    assert the_corpus.guid == corpus.guid
    assert the_corpus.checksum == corpus.checksum

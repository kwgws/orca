import asyncio
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from orca.model import Document, Search
from orca.tasks import create_index, create_search, import_documents


@pytest.mark.asyncio
async def test_get_session(session):
    assert isinstance(session, AsyncSession)
    assert session.is_active


@pytest.mark.asyncio
async def test_search(session, tmp_path):
    assert isinstance(session, AsyncSession)

    json_paths = [
        Path(p)
        for p in [
            "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json",
            "00/json/2022-09/000002_2022-09-27_13-12-56_image_5993.json",
            "00/json/2022-09/000003_2022-09-27_13-13-04_image_5994.json",
            "00/json/2022-09/000004_2022-09-27_13-13-31_image_5995.json",
            "00/json/2022-09/000005_2022-09-27_13-15-10_image_5996.json",
        ]
    ]
    text_paths = [
        Path(str(p).replace("/json", "/text").replace(".json", ".txt"))
        for p in json_paths
    ]

    await import_documents(json_paths, session=session)

    documents: list[Document] = await Document.get_all(session=session)
    for i, doc in enumerate(documents):
        assert Path(doc.json_path) == json_paths[i]
        assert Path(doc.text_path) == text_paths[i]

    for i, txt_path in enumerate(doc.text_path for doc in documents):
        doc_text_path = tmp_path / txt_path
        doc_text_path.parent.mkdir(parents=True, exist_ok=True)
        doc_text_path.write_text(f"Hello from Document #{i + 1}")

    for i, doc in enumerate(documents):
        doc_text_path = tmp_path / doc.text_path
        assert doc_text_path.read_text() == f"Hello from Document #{i + 1}"

    for i, doc in enumerate(documents):
        assert (
            await asyncio.to_thread(doc.get_text, data_path=tmp_path)
            == f"Hello from Document #{i + 1}"
        )

    await create_index(
        index_path=tmp_path / "index", data_path=tmp_path, session=session
    )

    result: Search = await create_search(
        "Hello", index_path=tmp_path / "index", session=session
    )
    for doc in documents:
        assert doc in result.documents

    result: Search = await create_search(
        "Hella~1", index_path=tmp_path / "index", session=session
    )
    for doc in documents:
        assert doc in result.documents

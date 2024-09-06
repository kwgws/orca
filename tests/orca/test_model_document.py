from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from orca.model import Document, Scan


@pytest.mark.asyncio
async def test_get_session(session):
    assert isinstance(session, AsyncSession)
    assert session.is_active


@pytest.mark.asyncio
async def test_get_all_empty_database(session):
    assert await Scan.get_all(session=session) == []
    assert await Document.get_all(session=session) == []


@pytest.mark.asyncio
async def test_get_latest_empty_database(session):
    assert await Scan.get_latest(session=session) is None
    assert await Document.get_latest(session=session) is None


@pytest.mark.asyncio
async def test_create_document_from_file(session):
    assert isinstance(session, AsyncSession)

    path = "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json"
    document = await Document.create_from_file(path=path, scan=None, session=session)
    scan = document.scan

    assert isinstance(scan, Scan)
    assert scan.stem == "000001_2022-09-27_13-12-42_image_5992"
    assert scan.album == "2022-09"
    assert scan.album_index == 1
    assert scan.title == "image_5992"
    assert scan.path == "img/2022-09/000001_2022-09-27_13-12-42_image_5992.webp"
    assert scan.scanned_at == datetime(2022, 9, 27, 13, 12, 42)
    assert not scan.scanned_at.tzinfo

    assert isinstance(document, Document)
    assert document.scan_guid == scan.guid
    assert document.scan == scan
    assert document.json_path == path
    assert (
        document.text_path
        == "00/text/2022-09/000001_2022-09-27_13-12-42_image_5992.txt"
    )


@pytest.mark.asyncio
async def test_invalid_filename_format(session):
    invalid_paths = [
        "badfilename.json",
        "00/json/2022-09/some_invalid_filename.json",
        "00/json/2022-09/000001_invalid-date_format_image_5992.json",
    ]

    for path in invalid_paths:
        with pytest.raises(TypeError):
            await Document.create_from_file(path=path, scan=None, session=session)


@pytest.mark.asyncio
async def test_get_document(session):
    assert isinstance(session, AsyncSession)
    assert await Scan.get_total(session=session) == 0
    assert await Document.get_total(session=session) == 0

    path = "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json"
    document = await Document.create_from_file(path=path, scan=None, session=session)
    scan = document.scan
    assert isinstance(scan, Scan)
    assert isinstance(document, Document)

    scan_guid = scan.guid
    document_guid = document.guid
    assert await Scan.get(scan_guid, session=session) == scan
    assert await Document.get(document_guid, session=session) == document
    assert await Scan.get_total(session=session) == 1
    assert await Document.get_total(session=session) == 1
    assert scan in await Scan.get_all(session=session)
    assert document in await Document.get_all(session=session)


@pytest.mark.asyncio
async def test_update_document(session):
    assert isinstance(session, AsyncSession)

    path = "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json"
    document = await Document.create_from_file(path=path, scan=None, session=session)
    scan = document.scan
    assert isinstance(scan, Scan)
    assert isinstance(document, Document)

    assert document.json_path == path
    assert document.text_path == f"{path[:-5]}.txt".replace("json", "text")

    new_path = "00/json/2022-12/000952_2022-12-31_10-10-41_image_5042.json"
    await document.update({"json_path": new_path}, session=session)

    assert document.json_path != path
    assert document.json_path == new_path


@pytest.mark.asyncio
async def test_delete_document(session):
    assert isinstance(session, AsyncSession)

    path = "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json"
    document = await Document.create_from_file(path=path, scan=None, session=session)
    scan = document.scan
    assert isinstance(scan, Scan)
    assert isinstance(document, Document)

    scan_guid = scan.guid
    document_guid = document.guid
    assert await Scan.get(scan_guid, session=session)
    assert await Document.get(document_guid, session=session)
    await scan.delete(session=session)
    # await document.delete(session=session) (should delete orphans)
    assert not await Scan.get(scan_guid, session=session)
    assert not await Document.get(document_guid, session=session)


@pytest.mark.asyncio
async def test_document_as_dict(session):
    assert isinstance(session, AsyncSession)

    json_path = "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json"
    text_path = "00/text/2022-09/000001_2022-09-27_13-12-42_image_5992.txt"
    document = await Document.create_from_file(
        path=json_path, scan=None, session=session
    )
    scan = document.scan
    assert isinstance(scan, Scan)
    assert isinstance(document, Document)

    # test scan dictionary
    scan_dict = scan.as_dict(to_js=False)
    assert scan_dict["stem"] == "000001_2022-09-27_13-12-42_image_5992"
    assert scan_dict["album"] == "2022-09"
    assert scan_dict["album_index"] == 1
    assert scan_dict["title"] == "image_5992"
    assert scan_dict["path"] == "img/2022-09/000001_2022-09-27_13-12-42_image_5992.webp"
    assert scan_dict["url"].endswith(
        "img/2022-09/000001_2022-09-27_13-12-42_image_5992.webp"
    )
    assert scan_dict["thumb_url"].endswith(
        "thumbs/2022-09/000001_2022-09-27_13-12-42_image_5992.webp"
    )
    assert scan_dict["scanned_at"] == "2022-09-27T13:12:42+00:00"
    assert scan_dict["media_created_at"] == "1970-01-01T00:00:00+00:00"

    # test document dictionary
    document_dict = document.as_dict(
        excl={"scan_guid", "json_path", "text_path", "path"}, to_js=True
    )
    assert "scanGuid" not in document_dict.keys()
    assert document_dict["jsonUrl"].endswith(json_path)
    assert "jsonPath" not in document_dict.keys()
    assert document_dict["textUrl"].endswith(text_path)
    assert "textPath" not in document_dict.keys()
    assert document_dict["scan"]["stem"] == scan_dict["stem"]
    assert document_dict["scan"]["album"] == scan_dict["album"]
    assert document_dict["scan"]["albumIndex"] == scan_dict["album_index"]
    assert document_dict["scan"]["title"] == scan_dict["title"]
    assert "path" not in document_dict["scan"].keys()
    assert document_dict["scan"]["url"] == scan_dict["url"]
    assert document_dict["scan"]["thumbUrl"] == scan_dict["thumb_url"]
    assert document_dict["scan"]["scannedAt"] == scan_dict["scanned_at"]
    assert document_dict["scan"]["mediaCreatedAt"] == scan_dict["media_created_at"]


@pytest.mark.asyncio
async def test_document_text(session, tmp_path):
    assert isinstance(session, AsyncSession)

    json_paths = [
        "00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json",
        "00/json/2022-09/000002_2022-09-27_13-12-56_image_5993.json",
        "00/json/2022-09/000003_2022-09-27_13-13-04_image_5994.json",
        "00/json/2022-09/000004_2022-09-27_13-13-31_image_5995.json",
        "00/json/2022-09/000005_2022-09-27_13-15-10_image_5996.json",
    ]
    text_paths = [
        p.replace("/json", "/text").replace(".json", ".txt") for p in json_paths
    ]
    documents: list[Document] = [
        await Document.create_from_file(path=p, scan=None, session=session)
        for p in json_paths
    ]
    for i, doc in enumerate(documents):
        assert doc.json_path == json_paths[i]
        assert doc.text_path == text_paths[i]

    for i, txt_path in enumerate(doc.text_path for doc in documents):
        doc_text_path = tmp_path / txt_path
        doc_text_path.parent.mkdir(parents=True, exist_ok=True)
        doc_text_path.write_text(f"Hello from Document #{i + 1}")

    for i, doc in enumerate(documents):
        doc_text_path = tmp_path / doc.text_path
        assert doc_text_path.read_text() == f"Hello from Document #{i + 1}"

    for i, doc in enumerate(documents):
        assert (
            await doc.get_text_async(data_path=tmp_path)
            == f"Hello from Document #{i + 1}"
        )


@pytest.mark.asyncio
async def test_get_json_file_not_found(session, tmp_path):
    document = await Document.create_from_file(
        path="00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json",
        scan=None,
        session=session,
    )
    json_data = await document.get_json_async(data_path=tmp_path)
    assert json_data == {}


@pytest.mark.asyncio
async def test_get_text_file_not_found(session, tmp_path):
    document = await Document.create_from_file(
        path="00/json/2022-09/000001_2022-09-27_13-12-42_image_5992.json",
        scan=None,
        session=session,
    )
    text_data = await document.get_text_async(data_path=tmp_path)
    assert text_data == ""

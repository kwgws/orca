from orca.model import Corpus, Document, Image, Megadoc, Search


def test_document(session):
    image = Image.create_from_file(
        "00/json/001/000001_2022-09-27_13-12-42_IMG_5992.json", session=session
    )
    assert image.index == 1
    assert image.album == "001"
    assert image.title == "IMG_5992"
    assert image in Image.get_all(session=session)
    assert Document.get_total(session=session) == 1
    assert image.as_dict()

    doc = Document.get_all(session=session)[0]
    assert doc
    assert doc.batch == "00"
    assert doc.as_dict()

    image.delete(session=session)
    assert Document.get_total(session=session) == 0


def test_results(session):
    image = Image.create_from_file(
        "00/json/001/000001_2022-09-27_13-12-42_IMG_5992.json", session=session
    )
    doc = image.documents[0]
    assert doc
    assert len(doc.searches) == 0

    search = Search.create("test query", session=session)
    assert search
    assert search in Search.get_all(session=session)
    assert search.results == 0
    assert search.as_dict()

    search.add_document(doc, session=session)
    assert doc in search.documents

    megadoc = search.add_megadoc(".txt", session=session)
    assert megadoc
    assert megadoc.filename
    assert megadoc.path
    assert megadoc.url
    assert megadoc.as_dict()["filetype"] == ".txt"
    assert megadoc in Megadoc.get_all(session=session)
    assert megadoc.search == search
    assert megadoc.filesize == 0
    assert search.results == 1
    assert megadoc.as_dict()

    corpus = Corpus.create(session=session)
    assert doc in corpus.documents
    assert search in corpus.searches
    assert doc.id in corpus.as_dict()["documents"]
    assert search.id in corpus.as_dict()["searches"]
    assert len(corpus.hash) == 64
    assert corpus.color.startswith("#")

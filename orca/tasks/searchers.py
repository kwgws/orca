import logging

from whoosh import index
from whoosh.qparser import FuzzyTermPlugin, QueryParser

from orca import _config
from orca.model import Document, Search, with_session
from orca.tasks.celery import celery

log = logging.getLogger(__name__)


@celery.task(bind=True)
@with_session
def run_search(self, search_str: str, session=None):
    """ """
    search = Search.create(search_str, session=session)
    if not search:
        raise RuntimeError(f"Could not create search `{search_str}`")
    log.info(f"Starting search `{search_str}`")
    search.set_status("STARTED", session=session)

    # Load Whoosh index
    ix = index.open_dir(_config.INDEX_PATH.as_posix())
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema)
        parser.add_plugin(FuzzyTermPlugin())

        # Parse query and perform search
        query = parser.parse(search_str)
        for result in searcher.search(query, limit=None):
            document = Document.get(result["uid"], session=session)
            if not document:
                raise LookupError(f"Tried accessing invalid document: {result['uid']}")
            if document in search.documents:
                log.warning(f"Tried re-adding {result['uid']} to `{search_str}`")
                continue
            search.add_document(document, session=session)

    log.info(f"Finished search `{search_str}`, {len(search.documents)} results")
    search.set_status("SUCCESS", session=session)
    return search.uid

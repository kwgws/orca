import logging
import mimetypes

import boto3
from botocore.exceptions import BotoCoreError
from whoosh import index
from whoosh.qparser import FuzzyTermPlugin, QueryParser

from orca import config
from orca.model import Document, Megadoc, Search, with_session
from orca.tasks.celery import celery

log = logging.getLogger("orca")


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
    ix = index.open_dir(config.INDEX_PATH.as_posix())
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema)
        parser.add_plugin(FuzzyTermPlugin())

        # Parse query and perform search
        query = parser.parse(search_str)
        for result in searcher.search(query, limit=None):
            document = Document.get(result["id"], session=session)
            if not document:
                raise LookupError(f"Tried accessing invalid document: {result['id']}")
            if document in search.documents:
                log.warning(f"Tried re-adding {result['id']} to `{search_str}`")
                continue
            search.add_document(document, session=session)

    log.info(f"Finished search `{search_str}`, {len(search.documents)} results")
    search.set_status("SUCCESS", session=session)
    return search.id


@celery.task(bind=True)
@with_session
def create_megadoc(self, search_id: str, filetype, session=None):
    """ """
    search = Search.get(search_id, session=session)
    if not search:
        raise LookupError(f"Tried creating megadoc for invalid search {search_id}")

    # Look for a pre-existing megadoc
    megadoc = None
    for md in search.megadocs:
        if md.filetype == filetype:
            log.warning(f"Search `{search.search_str}` already has {filetype} megadoc")
            # if md.status == "SENDING" or md.status == "SUCCESS":
            #     return md.id
            (config.DATA_PATH / md.path).unlink(missing_ok=True)
            megadoc = md

    # Otherwise, create a new one
    if not megadoc:
        megadoc = search.add_megadoc(filetype, session=session)

    log.info(f"Creating {filetype} megadoc for search `{search.search_str}`")
    documents = sorted(search.documents, key=lambda doc: doc.created)
    for doc in documents:
        if megadoc.status != "STARTED":
            megadoc.set_status("STARTED", session=session)
        if megadoc.filetype == ".docx":
            doc.to_docx(config.DATA_PATH / megadoc.path)
        else:
            doc.to_markdown(config.DATA_PATH / megadoc.path)

    # Set status to "SENDING" to indicate we're ready for upload
    megadoc.set_status("SENDING", session=session)
    return megadoc.id


@celery.task(bind=True)
@with_session
def upload_megadoc(self, megadoc_id, session=None):
    """ """
    megadoc = Megadoc.get(megadoc_id, session=session)
    if not megadoc:
        raise LookupError(f"Tried uploading invalid megadoc: {megadoc_id}")
    log.info(
        f"Uploading {megadoc.filetype} megadoc for `{megadoc.search.search_str}`"
        f" to S3 bucket at {config.CDN_ENDPOINT}"
    )

    local_path_str = (config.DATA_PATH / megadoc.path).as_posix()
    content_type, _ = mimetypes.guess_type(local_path_str)
    if content_type is None:
        content_type = "application/octet-stream"

    try:
        s3_session = boto3.session.Session()
        s3_client = s3_session.client(
            "s3",
            region_name=config.CDN_REGION,
            endpoint_url=config.CDN_ENDPOINT,
            aws_access_key_id=config.CDN_ACCESS_KEY,
            aws_secret_access_key=config.CDN_SECRET_KEY,
        )
        s3_client.upload_file(
            local_path_str,
            config.CDN_SPACE_NAME,
            megadoc.path,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": content_type,
                "ContentDisposition": "attachment",
            },
        )

    except BotoCoreError as e:
        log.error(f"Error uploading megadoc: {e}")
        raise self.retry(exc=e)

    log.info(f"Done uploading {megadoc.url}")
    megadoc.set_status("SUCCESS", session=session)
    return megadoc.id

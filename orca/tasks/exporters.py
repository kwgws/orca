import logging
import mimetypes

import boto3
from botocore.exceptions import BotoCoreError

from orca import config
from orca.model import Megadoc, Search, with_session
from orca.tasks import celery

log = logging.getLogger(__name__)


@celery.task(bind=True)
@with_session
def create_megadoc(self, search_uid: str, filetype, session=None):
    """ """
    log.info(f"Creating {filetype} megadoc for search with id {search_uid}")
    if not (search := Search.get(search_uid, session=session)):
        raise LookupError(f"Tried creating megadoc for invalid search {search_uid}")
    if not search.documents or len(search.documents) == 0:
        log.warning(f"No results for `{search.searchStr}`, skipping megadoc")
        return

    # Look for a pre-existing megadoc
    if megadoc := next((md for md in search.megadocs if md.filetype == filetype), None):
        log.warning(f"Search `{search.search_str}` already has {filetype} megadoc")
        (config.data_path / megadoc.path).unlink(missing_ok=True)  # delete file

    # Otherwise, create a new one
    else:
        megadoc = search.add_megadoc(filetype, session=session)

    megadoc.set_status("STARTED", session=session)
    for doc in sorted(search.documents, key=lambda doc: doc.created_at):
        if megadoc.filetype == ".docx":
            doc.to_docx_file(megadoc.full_path)
        else:
            doc.to_markdown_file(megadoc.full_path)
        megadoc.tick()

    # Set status to "SENDING" to indicate we're ready for upload
    megadoc.set_status("SENDING", session=session)
    return megadoc.uid


@celery.task(bind=True)
@with_session
def upload_megadoc(self, megadoc_uid, session=None):
    """ """
    if not (megadoc := Megadoc.get(megadoc_uid, session=session)):
        raise LookupError(f"Tried uploading invalid megadoc: {megadoc_uid}")
    if not megadoc.full_path.is_file():
        raise FileNotFoundError(f"File not found: {megadoc.full_path}")
    log.info(
        f"Uploading {megadoc.filetype} megadoc for `{megadoc.search.search_str}`"
        f" to S3 bucket at {config.cdn.endpoint}"
    )

    file_path = megadoc.full_path.as_posix()
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    try:
        s3_session = boto3.session.Session()
        s3_client = s3_session.client(
            "s3",
            region_name=config.cdn.region,
            endpoint_url=config.cdn.endpoint,
            aws_access_key_id=config.cdn.access_key,
            aws_secret_access_key=config.cdn.secret_key,
        )
        s3_client.upload_file(
            file_path,
            config.cdn.space,
            megadoc.path,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": content_type,
                "ContentDisposition": "attachment",
            },
        )

    except BotoCoreError as e:
        log.error(f"Error uploading megadoc: {e}")
        raise self.retry(exc=e) from e

    log.info(f"Done uploading {megadoc.url}")
    megadoc.set_status("SUCCESS", session=session)
    return megadoc.uid

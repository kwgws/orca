import logging
import mimetypes

import boto3
from botocore.exceptions import BotoCoreError

from orca import _config
from orca.model import Megadoc, Search, with_session
from orca.tasks.celery import celery

log = logging.getLogger(__name__)


@celery.task(bind=True)
@with_session
def create_megadoc(self, search_uid: str, filetype, session=None):
    """ """
    if not (search := Search.get(search_uid, session=session)):
        raise LookupError(f"Tried creating megadoc for invalid search {search_uid}")

    # Look for a pre-existing megadoc
    if megadoc := next((md for md in search.megadocs if md.filetype == filetype), None):
        log.warning(f"Search `{search.search_str}` already has {filetype} megadoc")
        (_config.DATA_PATH / megadoc.path).unlink(missing_ok=True)  # delete file

    # Otherwise, create a new one
    else:
        megadoc = search.add_megadoc(filetype, session=session)

    log.info(f"Creating {filetype} megadoc for search `{search.search_str}`")
    for doc in sorted(search.documents, key=lambda doc: doc.created_at):
        megadoc.set_status("STARTED", session=session)
        if megadoc.filetype == ".docx":
            doc.to_docx(_config.DATA_PATH / megadoc.path)
        else:
            doc.to_markdown(_config.DATA_PATH / megadoc.path)
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
        f" to S3 bucket at {_config.CDN_ENDPOINT}"
    )

    file_path = megadoc.full_path.as_posix()
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    try:
        s3_session = boto3.session.Session()
        s3_client = s3_session.client(
            "s3",
            region_name=_config.CDN_REGION,
            endpoint_url=_config.CDN_ENDPOINT,
            aws_access_key_id=_config.CDN_ACCESS_KEY,
            aws_secret_access_key=_config.CDN_SECRET_KEY,
        )
        s3_client.upload_file(
            file_path,
            _config.CDN_SPACE_NAME,
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

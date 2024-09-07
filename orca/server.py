import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from orca import app
from orca.model import get_async_session

log = logging.getLogger(__name__)

api = FastAPI()
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/")
async def index(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> JSONResponse:
    try:
        return JSONResponse(await app.export_corpus(session=session))
    except Exception:
        log.exception("Error retrieving status")
        raise HTTPException(500, "Internal server error")


@api.get("/search/{search_guid}")
async def get_search(
    search_guid: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> JSONResponse:
    try:
        search = await app.export_search(search_guid, session=session)
        if search != {}:
            return JSONResponse(search)
        raise HTTPException(404, f"Search <{search_guid}> not found")
    except Exception:
        log.exception("Error retrieving Search <%s>", search_guid)
        raise HTTPException(500, "Internal server error")


@api.post("/search")
async def create_search(
    request: Request,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> JSONResponse:
    if not (data := await request.json()):
        raise HTTPException(400, "Empty request")
    if not (search_str := data.get("search_str")):
        raise HTTPException(400, "Invalid request")
    try:
        search = await app.create_search(search_str, session=session)
        return JSONResponse({}, 202, {"Location": f"/search/{search.guid}"})
    except Exception:
        log.exception("Error creating search '%s'", search_str)
        raise HTTPException(500, "Internal server error")


@api.delete("/search/{search_guid}")
async def delete_search(
    search_guid: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> JSONResponse:
    try:
        if await app.delete_search(search_guid, session=session):
            return JSONResponse({}, 204)
        raise HTTPException(404, f"Search <{search_guid}> not found")
    except Exception:
        log.exception("Error deleting Search <%s>", search_guid)
        raise HTTPException(500, "Internal server error")

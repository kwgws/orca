import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from orca import app
from orca.helpers import deserialize
from orca.model import get_async_session, init_async_engine, teardown_async_engine

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(api: FastAPI):
    await init_async_engine()
    yield
    await teardown_async_engine()


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        async with get_async_session() as session:
            request.state.db = session
            try:
                response = await call_next(request)
            finally:
                pass
        return response


api = FastAPI(lifespan=lifespan)
api.add_middleware(DBSessionMiddleware)
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/")
async def index(request: Request) -> JSONResponse:
    session: AsyncSession = request.state.db
    try:
        return JSONResponse(await app.export_corpus(session=session))
    except Exception:
        log.exception("Error retrieving status")
        raise HTTPException(500, "Internal server error")


@api.get("/search/{search_guid}")
async def get_search(search_guid: str, request: Request) -> JSONResponse:
    session: AsyncSession = request.state.db
    try:
        search = await app.export_search(search_guid, session=session)
        if search != {}:
            return JSONResponse(search)
        raise HTTPException(404, f"Search <{search_guid}> not found")
    except Exception:
        log.exception("Error retrieving Search <%s>", search_guid)
        raise HTTPException(500, "Internal server error")


@api.post("/search")
async def create_search(request: Request) -> Response:
    session: AsyncSession = request.state.db
    if not (data := await request.json()):
        raise HTTPException(400, "Empty request")
    if not (search_str := deserialize(data, from_js=True).get("search_str")):
        raise HTTPException(400, "Invalid request")
    try:
        search = await app.create_search(search_str, session=session)
        return Response(status_code=201, headers={"Location": f"/search/{search.guid}"})
    except Exception:
        log.exception("Error creating search '%s'", search_str)
        raise HTTPException(500, "Internal server error")


@api.delete("/search/{search_guid}")
async def delete_search(search_guid: str, request: Request) -> Response:
    session: AsyncSession = request.state.db
    try:
        if await app.delete_search(search_guid, session=session):
            return Response(status_code=204)
        raise HTTPException(404, f"Search <{search_guid}> not found")
    except Exception:
        log.exception("Error deleting Search <%s>", search_guid)
        raise HTTPException(500, "Internal server error")

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app import crud
from app.config import SEED_SAMPLE_DATA
from app.database import engine, init_db, seed_sample_data
from app.routes import claims, items


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if SEED_SAMPLE_DATA:
        with Session(engine) as session:
            seed_sample_data(session)
    yield


def _domain_error_response(_: Request, error: crud.DomainError) -> JSONResponse:
    status_code = 409
    if isinstance(error, crud.ItemNotFoundError):
        status_code = 404
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


app = FastAPI(
    title="Campus Lost & Found API",
    version="0.1.0",
    description="API for reporting, searching, and claiming lost or found items on campus.",
    lifespan=lifespan,
)
app.add_exception_handler(crud.DomainError, _domain_error_response)
app.include_router(items.router)
app.include_router(claims.router)

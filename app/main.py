from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app import crud
from app.config import SEED_SAMPLE_DATA
from app import database as db
from app.database import init_db, seed_sample_data
from app.routes import claims, items
from app.routes import pages

from pathlib import Path
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with Session(db.engine) as session:
        from app.accounts import ensure_demo_user

        ensure_demo_user(session)
        if SEED_SAMPLE_DATA:
            seed_sample_data(session)
    yield


def _domain_error_response(_: Request, error: crud.DomainError) -> JSONResponse:
    status_code = 409
    if isinstance(error, (crud.ItemNotFoundError, crud.ClaimNotFoundError)):
        status_code = 404
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


app = FastAPI(
    title="Campus Lost & Found API",
    version="0.1.0",
    description="API for reporting, searching, and claiming lost or found items on campus.",
    lifespan=lifespan,
)
app.add_exception_handler(crud.DomainError, _domain_error_response)
app.include_router(pages.router)
app.include_router(items.router)
app.include_router(claims.router)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# serve CSS/images
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")),
          name="static")

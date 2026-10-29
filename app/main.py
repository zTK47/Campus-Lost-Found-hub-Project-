from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine, init_db, seed_sample_data
from app.routes import claims, items
from sqlmodel import Session


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with Session(engine) as session:
        seed_sample_data(session)
    yield


app = FastAPI(
    title="Campus Lost & Found API",
    version="0.1.0",
    description="API for reporting, searching, and claiming lost or found items on campus.",
    lifespan=lifespan,
)
app.include_router(items.router)
app.include_router(claims.router)

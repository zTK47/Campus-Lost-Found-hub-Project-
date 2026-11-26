import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

os.environ.setdefault("DB_URL", "sqlite://")

from app import database as database_module
from app.database import get_session, seed_sample_data
from app.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Point the app (and auth.current_user) at the same in-memory engine.
    database_module.engine = engine

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_sample_data(session)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

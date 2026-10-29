import os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine as create_sqlalchemy_engine, text
from sqlmodel import Session, SQLModel, create_engine

from app.database import seed_sample_data
from app.main import app
from app.database import get_session
from fastapi.testclient import TestClient


TEST_MYSQL_URL = os.getenv("TEST_MYSQL_URL")
pytestmark = pytest.mark.skipif(
    not TEST_MYSQL_URL,
    reason="TEST_MYSQL_URL is not set",
)


@pytest.fixture(scope="session")
def mysql_engine():
    assert TEST_MYSQL_URL
    parsed = urlsplit(TEST_MYSQL_URL)
    database_name = "campus_lost_found_test"
    server_url = (
        f"mysql+pymysql://{parsed.username}:{parsed.password or ''}"
        f"@{parsed.hostname}:{parsed.port or 3306}/"
    )
    server_engine = create_sqlalchemy_engine(server_url, pool_pre_ping=True)
    with server_engine.begin() as connection:
        connection.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                "CHARACTER SET utf8mb4"
            )
        )
    server_engine.dispose()

    test_url = (
        f"mysql+pymysql://{parsed.username}:{parsed.password or ''}"
        f"@{parsed.hostname}:{parsed.port or 3306}/{database_name}?charset=utf8mb4"
    )
    engine = create_engine(test_url, pool_pre_ping=True, pool_recycle=3600)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(mysql_engine):
    SQLModel.metadata.drop_all(mysql_engine)
    SQLModel.metadata.create_all(mysql_engine)
    with Session(mysql_engine) as session:
        seed_sample_data(session)

    def override_session():
        with Session(mysql_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def claim_payload(name="Alex Example"):
    return {
        "claimant_name": name,
        "claimant_contact": f"{name.lower().replace(' ', '.')}@example.com",
        "proof_description": "A hidden detail",
    }


def test_mysql_core_item_and_claim_scenarios(client):
    created = client.post("/items", json={
        "title": "Green bag",
        "category": "bag",
        "location_found": "Library",
        "date_found": "2026-10-01",
        "finder_contact": "finder@example.com",
    })
    assert created.status_code == 201
    assert client.get("/items", params={"category": "bag"}).status_code == 200
    assert client.post("/items/12/claims", json=claim_payload()).status_code == 201
    assert client.post("/items/12/claims", json=claim_payload("Second Claimant")).status_code == 409
    assert client.patch("/items/12", json={"status": "returned"}).status_code == 200


def test_mysql_concurrent_duplicate_claim(client):
    def submit_claim(index):
        with TestClient(app) as concurrent_client:
            return concurrent_client.post(
                "/items/12/claims",
                json=claim_payload(f"Claimant {index}"),
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(submit_claim, (1, 2)))
    assert sorted(statuses) == [201, 409]

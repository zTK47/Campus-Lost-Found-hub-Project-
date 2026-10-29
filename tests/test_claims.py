from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import crud
from app.database import get_session, seed_sample_data
from app.main import app
from app.schemas import ClaimCreate


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


def test_claim_invalid_input_rejected(client):
    response = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example",
        "claimant_contact": "alex@example.com",
        "proof_description": "",
    })
    assert response.status_code == 422


def test_claim_open_item_succeeds(client):
    response = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example",
        "claimant_contact": "alex@example.com",
        "proof_description": "The sticker shows a mountain and there is a dent near the lid.",
    })
    assert response.status_code == 201
    assert response.json()["item_id"] == 12
    assert "proof_description" not in response.json()
    assert datetime.fromisoformat(response.json()["created_at"]).tzinfo is not None


def test_claim_already_claimed_item_rejected(client):
    client.post("/items/12/claims", json={
        "claimant_name": "First Claimant", "claimant_contact": "a@example.com",
        "proof_description": "something",
    })
    response = client.post("/items/12/claims", json={
        "claimant_name": "Second Claimant", "claimant_contact": "b@example.com",
        "proof_description": "something else",
    })
    assert response.status_code == 409


def test_create_item_validates_category_date_and_required_fields(client):
    payload = {
        "title": "Green bag",
        "category": "bag",
        "location_found": "Library",
        "date_found": "2026-10-01",
        "finder_contact": "finder@example.com",
    }
    response = client.post("/items", json=payload)
    assert response.status_code == 201
    assert "finder_contact" not in response.json()

    assert client.post("/items", json={**payload, "category": "food"}).status_code == 422
    assert client.post("/items", json={**payload, "date_found": "2099-01-01"}).status_code == 422
    assert client.post("/items", json={**payload, "title": ""}).status_code == 422


def test_list_filters_pagination_and_hides_returned_items(client):
    assert client.get("/items", params={"q": "BLUE"}).json()["count"] == 1
    assert client.get("/items", params={"location": "LECTURE"}).json()["count"] == 1

    payload = {
        "title": "Red jacket",
        "category": "clothing",
        "description": "Found near the north entrance",
        "location_found": "North entrance",
        "date_found": "2026-10-01",
        "finder_contact": "finder@example.com",
    }
    created = client.post("/items", json=payload).json()
    assert client.patch(f"/items/{created['id']}", json={"status": "returned"}).status_code == 200
    assert client.get("/items", params={"q": "jacket"}).json()["count"] == 0
    assert client.get("/items", params={"status": "returned"}).json()["count"] == 1
    page = client.get("/items", params={"limit": 1, "offset": 1}).json()
    assert page["limit"] == 1
    assert page["offset"] == 1
    assert all("finder_contact" not in item for item in page["items"])
    assert client.get("/items", params={"q": "JACKET"}).json()["count"] == 0
    assert client.get("/items", params={"location": "NORTH"}).json()["count"] == 0
    assert client.get("/items", params={"limit": 101}).status_code == 422
    assert client.get("/items", params={"category": "unknown"}).status_code == 422
    assert client.get("/items", params={"status": "expired"}).status_code == 422


def test_get_item_and_status_transition_errors(client):
    missing = client.get("/items/999")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Item 999 not found"}
    detail = client.get("/items/12")
    assert detail.status_code == 200
    assert "finder_contact" not in detail.json()
    assert client.patch("/items/12", json={"status": "returned"}).status_code == 200
    assert client.patch("/items/12", json={"status": "open"}).status_code == 409
    assert client.patch("/items/12", json={"unknown": "value"}).status_code == 422
    assert client.patch("/items/12", json={}).status_code == 409
    assert client.get("/items/-1").status_code == 422


def test_status_transitions_allow_reopen_and_return_once(client):
    claim = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example",
        "claimant_contact": "alex@example.com",
        "proof_description": "A hidden detail",
    })
    assert claim.status_code == 201
    assert client.patch("/items/12", json={"status": "open"}).status_code == 200
    assert client.post("/items/12/claims", json={
        "claimant_name": "Second Claimant",
        "claimant_contact": "second@example.com",
        "proof_description": "Another hidden detail",
    }).status_code == 201
    assert client.patch("/items/12", json={"status": "returned"}).status_code == 200
    assert client.patch("/items/12", json={"status": "open"}).status_code == 409


def test_claims_detail_is_finder_only_view(client):
    client.post("/items/12/claims", json={
        "claimant_name": "Alex Example",
        "claimant_contact": "alex@example.com",
        "proof_description": "A hidden detail",
    })
    response = client.get("/items/12/claims")
    assert response.status_code == 200
    assert response.json()[0]["proof_description"] == "A hidden detail"


def test_claim_missing_item_returns_not_found(client):
    response = client.post("/items/999/claims", json={
        "claimant_name": "Alex Example",
        "claimant_contact": "alex@example.com",
        "proof_description": "A hidden detail",
    })
    assert response.status_code == 404
    assert response.json() == {"detail": "Item 999 not found"}


def test_concurrent_claims_only_one_succeeds(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrency.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_sample_data(session)

    barrier = Barrier(2)

    def submit_claim(index: int) -> int:
        claim = ClaimCreate(
            claimant_name=f"Claimant {index}",
            claimant_contact=f"claimant{index}@example.com",
            proof_description="A hidden detail",
        )
        with Session(engine) as session:
            barrier.wait()
            try:
                crud.create_claim(session, 12, claim)
            except crud.ItemNotOpenError:
                return 409
            return 201

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(submit_claim, (1, 2)))

    assert sorted(statuses) == [201, 409]

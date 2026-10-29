import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session, seed_sample_data
from app.main import app


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


def test_get_item_and_status_transition_errors(client):
    assert client.get("/items/999").status_code == 404
    assert client.patch("/items/12", json={"status": "returned"}).status_code == 200
    assert client.patch("/items/12", json={"status": "open"}).status_code == 409
    assert client.patch("/items/12", json={"unknown": "value"}).status_code == 422


def test_claims_detail_is_finder_only_view(client):
    client.post("/items/12/claims", json={
        "claimant_name": "Alex Example",
        "claimant_contact": "alex@example.com",
        "proof_description": "A hidden detail",
    })
    response = client.get("/items/12/claims")
    assert response.status_code == 200
    assert response.json()[0]["proof_description"] == "A hidden detail"

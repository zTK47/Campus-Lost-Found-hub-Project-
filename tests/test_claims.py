from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier

from sqlmodel import Session, SQLModel, create_engine

from app import crud
from app.database import seed_sample_data
from app.schemas import ClaimCreate


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

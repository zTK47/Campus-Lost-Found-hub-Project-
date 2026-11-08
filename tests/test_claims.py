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
    response = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example",
        "claimant_contact": "alex@example.com",
        "proof_description": "x" * 2001,
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
    assert response.json()["status"] == "pending"
    assert "proof_description" not in response.json()
    assert datetime.fromisoformat(response.json()["created_at"]).tzinfo is not None


def test_several_claims_allowed_while_item_open(client):
    first = client.post("/items/12/claims", json={
        "claimant_name": "First Claimant", "claimant_contact": "a@example.com",
        "proof_description": "something",
    })
    second = client.post("/items/12/claims", json={
        "claimant_name": "Second Claimant", "claimant_contact": "b@example.com",
        "proof_description": "something else",
    })
    assert first.status_code == second.status_code == 201
    assert client.get("/items/12").json()["status"] == "open"
    assert client.get("/items/12").json()["claim_count"] == 2


def test_accept_claim_updates_item_and_rejects_siblings(client):
    first = client.post("/items/12/claims", json={
        "claimant_name": "First Claimant", "claimant_contact": "a@example.com",
        "proof_description": "something",
    }).json()
    second = client.post("/items/12/claims", json={
        "claimant_name": "Second Claimant", "claimant_contact": "b@example.com",
        "proof_description": "something else",
    }).json()
    response = client.patch(
        f"/items/12/claims/{first['id']}", json={"status": "accepted"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert client.get("/items/12").json()["status"] == "claimed"
    claims = client.get("/items/12/claims").json()
    assert {claim["id"]: claim["status"] for claim in claims} == {
        first["id"]: "accepted",
        second["id"]: "rejected",
    }


def test_accept_unknown_claim_returns_not_found(client):
    claim = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example", "claimant_contact": "a@example.com",
        "proof_description": "something",
    }).json()
    assert client.patch("/items/12/claims/999", json={"status": "accepted"}).status_code == 404


def test_accept_claim_belonging_to_another_item_returns_not_found(client):
    claim = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example", "claimant_contact": "a@example.com",
        "proof_description": "something",
    }).json()
    other_item = client.post("/items", json={
        "title": "Green bag",
        "category": "bag",
        "location_found": "Library",
        "date_found": "2026-10-01",
        "finder_contact": "finder@example.com",
    }).json()
    assert client.patch(
        f"/items/{other_item['id']}/claims/{claim['id']}",
        json={"status": "accepted"},
    ).status_code == 404


def test_accept_rejected_status_returns_validation_error(client):
    claim = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example", "claimant_contact": "a@example.com",
        "proof_description": "something",
    }).json()
    assert client.patch("/items/12/claims/1", json={"status": "rejected"}).status_code == 422


def test_accept_empty_body_returns_validation_error(client):
    claim = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example", "claimant_contact": "a@example.com",
        "proof_description": "something",
    }).json()
    assert client.patch(
        f"/items/12/claims/{claim['id']}", json={}
    ).status_code == 422


def test_accept_already_accepted_claim_returns_conflict(client):
    claim = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example", "claimant_contact": "a@example.com",
        "proof_description": "something",
    }).json()
    assert client.patch(
        f"/items/12/claims/{claim['id']}", json={"status": "accepted"}
    ).status_code == 200
    assert client.patch(
        f"/items/12/claims/{claim['id']}", json={"status": "accepted"}
    ).status_code == 409


def test_reopening_rejects_accepted_claim_and_allows_new_claim(client):
    claim = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example", "claimant_contact": "a@example.com",
        "proof_description": "something",
    }).json()
    client.patch(f"/items/12/claims/{claim['id']}", json={"status": "accepted"})
    assert client.patch("/items/12", json={"status": "open"}).status_code == 200
    assert client.get("/items/12/claims").json()[0]["status"] == "rejected"
    response = client.post("/items/12/claims", json={
        "claimant_name": "New Claimant", "claimant_contact": "new@example.com",
        "proof_description": "new proof",
    })
    assert response.status_code == 201


def test_accept_claim_on_claimed_item_returns_conflict(client):
    claim = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example", "claimant_contact": "a@example.com",
        "proof_description": "something",
    }).json()
    assert client.patch(
        f"/items/12/claims/{claim['id']}", json={"status": "accepted"}
    ).status_code == 200
    response = client.patch(
        f"/items/12/claims/{claim['id']}", json={"status": "accepted"}
    )
    assert response.status_code == 409
    assert response.json() == {
        "detail": "Item 12 is claimed and cannot accept a claim decision."
    }


def test_accept_claim_on_returned_item_returns_conflict(client):
    claim = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example", "claimant_contact": "a@example.com",
        "proof_description": "something",
    }).json()
    client.patch(f"/items/12/claims/{claim['id']}", json={"status": "accepted"})
    assert client.patch("/items/12", json={"status": "returned"}).status_code == 200
    response = client.patch(
        f"/items/12/claims/{claim['id']}", json={"status": "accepted"}
    )
    assert response.status_code == 409
    assert response.json() == {
        "detail": "Item 12 is returned and cannot accept a claim decision."
    }


def test_accept_rejected_claim_returns_conflict(client):
    claim = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example", "claimant_contact": "a@example.com",
        "proof_description": "something",
    }).json()
    client.patch(f"/items/12/claims/{claim['id']}", json={"status": "accepted"})
    assert client.patch("/items/12", json={"status": "open"}).status_code == 200
    response = client.patch(
        f"/items/12/claims/{claim['id']}", json={"status": "accepted"}
    )
    assert response.status_code == 409
    assert response.json() == {
        "detail": "Claim 1 is already rejected and cannot be accepted."
    }


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


def test_concurrent_claim_acceptance_only_one_succeeds(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrency.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_sample_data(session)

    barrier = Barrier(2)
    claim_ids = []
    with Session(engine) as session:
        for index in (1, 2):
            claim_ids.append(
                crud.create_claim(
                    session,
                    12,
                    ClaimCreate(
                        claimant_name=f"Claimant {index}",
                        claimant_contact=f"claimant{index}@example.com",
                        proof_description="A hidden detail",
                    ),
                ).id
            )

    def accept_claim(claim_id: int) -> int:
        with Session(engine) as session:
            barrier.wait()
            try:
                crud.accept_claim(session, 12, claim_id)
            except (
                crud.ItemNotOpenError,
                crud.ItemNotOpenForAcceptanceError,
                crud.ClaimNotPendingError,
            ):
                return 409
            return 200

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(accept_claim, claim_ids))

    assert sorted(statuses) == [200, 409]

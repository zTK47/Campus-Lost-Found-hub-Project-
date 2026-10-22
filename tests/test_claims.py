from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_claim_open_item_succeeds():
    response = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example",
        "claimant_contact": "alex@example.com",
        "proof_description": "The sticker shows a mountain and there is a dent near the lid.",
    })
    assert response.status_code == 201
    assert response.json()["item_id"] == 12

def test_claim_already_claimed_item_rejected():
    # first claim succeeds and moves item 12 to "claimed"
    client.post("/items/12/claims", json={
        "claimant_name": "First Claimant", "claimant_contact": "a@example.com",
        "proof_description": "something",
    })
    # second claim on the same item should fail
    response = client.post("/items/12/claims", json={
        "claimant_name": "Second Claimant", "claimant_contact": "b@example.com",
        "proof_description": "something else",
    })
    assert response.status_code == 409
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

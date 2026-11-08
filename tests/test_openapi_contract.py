import json
import re
from pathlib import Path

import pytest

from app.main import app

OPENAPI_PATH = Path(__file__).parents[1] / "docs" / "openapi.json"


def test_exported_openapi_matches_application():
    assert json.loads(OPENAPI_PATH.read_text(encoding="utf-8")) == app.openapi()


def _readme_operations() -> list[tuple[str, str]]:
    readme = Path(__file__).parents[1] / "README.md"
    operations = []
    for line in readme.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\| .* \| `(GET|POST|PATCH) ([^`]+)` \|", line)
        if match:
            method, path = match.groups()
            operations.append((method.lower(), path.replace("{id}", "{item_id}")))
    return operations


@pytest.mark.parametrize("method,path", _readme_operations())
def test_endpoint_status_operation_exists_in_openapi(method: str, path: str):
    assert method in app.openapi()["paths"].get(path, {}), f"Missing {method.upper()} {path}"


def test_route_error_statuses_are_documented():
    expected = {
        ("post", "/items"): {"422"},
        ("get", "/items"): {"422"},
        ("get", "/items/{item_id}"): {"404", "422"},
        ("patch", "/items/{item_id}"): {"404", "409", "422"},
        ("post", "/items/{item_id}/claims"): {"404", "409", "422"},
        ("get", "/items/{item_id}/claims"): {"404", "422"},
        ("patch", "/items/{item_id}/claims/{claim_id}"): {"404", "409", "422"},
    }

    paths = app.openapi()["paths"]
    for method_path, status_codes in expected.items():
        method, path = method_path
        assert status_codes <= set(paths[path][method]["responses"])


def test_public_schemas_preserve_privacy_boundary():
    schemas = app.openapi()["components"]["schemas"]
    for schema_name in ("ItemPublic", "ItemDetail", "ClaimPublic"):
        properties = schemas[schema_name]["properties"]
        assert "finder_contact" not in properties
        assert "proof_description" not in properties
    assert "proof_description" in schemas["ClaimFinder"]["properties"]


def test_every_route_documents_validation_error_schema():
    for path, operations in app.openapi()["paths"].items():
        for method, operation in operations.items():
            if method not in {"get", "post", "patch"}:
                continue
            response = operation["responses"]["422"]
            assert response["content"]["application/json"]["schema"]["$ref"].endswith(
                "/ValidationErrorResponse"
            ), f"Missing validation schema for {method.upper()} {path}"


def test_documented_domain_error_examples_match_api(client):
    paths = app.openapi()["paths"]
    checks = [
        ("get", "/items/{item_id}", "/items/999", None, 404),
        ("patch", "/items/{item_id}", "/items/999", {"status": "returned"}, 404),
        ("patch", "/items/{item_id}", "/items/12", {"status": "claimed"}, 409),
        ("get", "/items/{item_id}/claims", "/items/999/claims", None, 404),
        ("patch", "/items/{item_id}/claims/{claim_id}", "/items/12/claims/999", {"status": "accepted"}, 404),
    ]
    for method, path, request_path, body, status in checks:
        operation = paths[path][method]
        example = operation["responses"][str(status)]["content"]["application/json"]["example"]
        response = client.request(method.upper(), request_path, json=body)
        assert response.status_code == status
        assert response.json()["detail"] == example["detail"]

    item_conflict = client.patch("/items/12", json={"status": "claimed"})
    item_example = paths["/items/{item_id}"]["patch"]["responses"]["409"]["content"][
        "application/json"
    ]["example"]
    assert item_conflict.status_code == 409
    assert item_conflict.json()["detail"] == item_example["detail"]

    claim = client.post("/items/12/claims", json={
        "claimant_name": "Alex Example",
        "claimant_contact": "alex@example.com",
        "proof_description": "proof",
    }).json()
    client.patch(f"/items/12/claims/{claim['id']}", json={"status": "accepted"})
    claim_conflict = client.post("/items/12/claims", json={
        "claimant_name": "Second Claimant",
        "claimant_contact": "second@example.com",
        "proof_description": "proof",
    })
    claim_create_example = paths["/items/{item_id}/claims"]["post"]["responses"]["409"][
        "content"
    ]["application/json"]["example"]
    assert claim_conflict.status_code == 409
    assert claim_conflict.json()["detail"] == claim_create_example["detail"]

    accept_conflict = client.patch(
        f"/items/12/claims/{claim['id']}", json={"status": "accepted"}
    )
    accept_examples = paths[
        "/items/{item_id}/claims/{claim_id}"
    ]["patch"]["responses"]["409"]["content"]["application/json"]["examples"]
    assert accept_conflict.status_code == 409
    assert accept_conflict.json()["detail"] == accept_examples["item_not_open"]["value"]["detail"]

    client.patch("/items/12", json={"status": "open"})
    first = client.post("/items/12/claims", json={
        "claimant_name": "First Claimant",
        "claimant_contact": "first@example.com",
        "proof_description": "first proof",
    }).json()
    rejected = client.post("/items/12/claims", json={
        "claimant_name": "Rejected Claimant",
        "claimant_contact": "rejected@example.com",
        "proof_description": "rejected proof",
    }).json()
    client.patch(f"/items/12/claims/{first['id']}", json={"status": "accepted"})
    client.patch("/items/12", json={"status": "open"})
    claim_not_pending = client.patch(
        f"/items/12/claims/{rejected['id']}", json={"status": "accepted"}
    )
    assert claim_not_pending.status_code == 409
    assert (
        claim_not_pending.json()["detail"]
        == accept_examples["claim_not_pending"]["value"]["detail"]
    )

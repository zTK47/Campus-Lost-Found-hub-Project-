import json
from pathlib import Path

from app.main import app


OPENAPI_PATH = Path(__file__).parents[1] / "docs" / "openapi.json"


def test_exported_openapi_matches_application():
    assert json.loads(OPENAPI_PATH.read_text(encoding="utf-8")) == app.openapi()


def test_endpoint_status_operations_exist_in_openapi():
    operations = {
        ("post", "/items"),
        ("get", "/items"),
        ("get", "/items/{item_id}"),
        ("patch", "/items/{item_id}"),
        ("post", "/items/{item_id}/claims"),
        ("get", "/items/{item_id}/claims"),
        ("patch", "/items/{item_id}/claims/{claim_id}"),
    }

    paths = app.openapi()["paths"]
    assert all(method in paths[path] for method, path in operations)


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

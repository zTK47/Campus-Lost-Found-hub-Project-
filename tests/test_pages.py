import pytest

PAGES = ["/", "/report", "/item", "/finder"]


@pytest.mark.parametrize("path", PAGES)
def test_frontend_pages_are_served_as_html(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Campus Lost & Found" in response.text


@pytest.mark.parametrize(
    "path,content_type",
    [
        ("/static/css/styles.css", "text/css"),
        ("/static/js/api.js", "text/javascript"),
        ("/static/js/common.js", "text/javascript"),
    ],
)
def test_frontend_assets_are_served(client, path, content_type):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)


def test_frontend_pages_are_not_part_of_the_api_contract(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert not any(page in paths for page in PAGES)

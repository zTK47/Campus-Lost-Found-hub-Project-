"""Web interface (presentation layer).

The pages are static HTML files in app/static. Their JavaScript calls the same
REST API that is documented in OpenAPI, so the frontend uses the API, the
business rules in app/crud.py and the database like any other client.
These routes are excluded from the OpenAPI contract because they return HTML.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

# Some Windows installations map .js to text/plain, which stops browsers from
# loading JavaScript modules. Registering the types keeps the pages working.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")

router = APIRouter(include_in_schema=False)


def _page(filename: str) -> FileResponse:
    return FileResponse(STATIC_DIR / filename, media_type="text/html")


@router.get("/")
def found_items_page() -> FileResponse:
    return _page("index.html")


@router.get("/report")
def report_page() -> FileResponse:
    return _page("report.html")


@router.get("/item")
def item_page() -> FileResponse:
    return _page("item.html")


@router.get("/finder")
def finder_page() -> FileResponse:
    return _page("finder.html")

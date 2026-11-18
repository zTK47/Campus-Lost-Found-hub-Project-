from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.database import get_session
from app import crud
from app.config import DEFAULT_PAGE_SIZE, CATEGORY_VALUES
from app.templating import templates   # or from main

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def items_list_page(
    request: Request,
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    status: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    items, count = crud.list_items(
        session,
        q=q,
        category=category,   # map to Category enum if needed
        location=location,
        status=status,       # map to ItemStatus if needed
        limit=limit,
        offset=offset,
    )
    return templates.TemplateResponse(
        "items_list.html",
        {
            "request": request,
            "items": items,
            "count": count,
            "limit": limit,
            "offset": offset,
            "q": q or "",
            "category": category or "",
            "location": location or "",
            "status": status or "",
            "categories": CATEGORY_VALUES,
            "message": request.query_params.get("message"),
            "message_error": request.query_params.get("error") == "1",
        },
    )

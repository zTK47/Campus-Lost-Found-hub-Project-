from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Path as PathParam, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlmodel import Session

from app import crud
from app.config import CATEGORY_VALUES, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.database import get_session
from app.models import ItemStatus
from app.schemas import Category, ClaimCreate, ItemCreate

router = APIRouter(tags=["pages"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

PositiveItemId = Annotated[int, PathParam(ge=1)]


def _flash_redirect(url: str, message: str, *, error: bool = False) -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    flag = "&error=1" if error else ""
    return RedirectResponse(
        url=f"{url}{sep}message={quote(message)}{flag}",
        status_code=303,
    )


def _validation_messages(exc: ValidationError) -> list[str]:
    messages: list[str] = []
    for err in exc.errors():
        loc = err.get("loc") or ()
        field = str(loc[-1]) if loc else "input"
        messages.append(f"{field}: {err.get('msg', 'invalid')}")
    return messages


def _parse_category(value: str | None) -> Category | None:
    if not value:
        return None
    try:
        return Category(value)
    except ValueError:
        return None


def _parse_status(value: str | None) -> ItemStatus | None:
    if not value:
        return None
    try:
        return ItemStatus(value)
    except ValueError:
        return None


@router.get("/", response_class=HTMLResponse)
def items_list_page(
    request: Request,
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    items, count = crud.list_items(
        session,
        q=q or None,
        category=_parse_category(category),
        location=location or None,
        status=_parse_status(status),
        limit=limit,
        offset=offset,
    )
    return templates.TemplateResponse(
        request,
        "items_list.html",
        {
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


@router.get("/report", response_class=HTMLResponse)
def report_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "report_item.html",
        {
            "categories": CATEGORY_VALUES,
            "errors": [],
            "form": {},
            "today": date.today().isoformat(),
            "message": request.query_params.get("message"),
            "message_error": request.query_params.get("error") == "1",
        },
    )


@router.post("/report")
def report_submit(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    location_found: str = Form(...),
    date_found: date = Form(...),
    finder_contact: str = Form(...),
    description: str | None = Form(None),
    session: Session = Depends(get_session),
):
    form_data = {
        "title": title,
        "category": category,
        "description": description or "",
        "location_found": location_found,
        "date_found": date_found.isoformat(),
        "finder_contact": finder_contact,
    }
    try:
        item_data = ItemCreate(
            title=title.strip(),
            category=Category(category),
            description=(description.strip() if description else None) or None,
            location_found=location_found.strip(),
            date_found=date_found,
            finder_contact=finder_contact.strip(),
        )
    except (ValidationError, ValueError) as exc:
        errors = (
            _validation_messages(exc)
            if isinstance(exc, ValidationError)
            else [str(exc)]
        )
        return templates.TemplateResponse(
            request,
            "report_item.html",
            {
                "categories": CATEGORY_VALUES,
                "errors": errors,
                "form": form_data,
                "today": date.today().isoformat(),
            },
            status_code=422,
        )

    item = crud.create_item(session, item_data)
    return _flash_redirect("/", f"Item {item.id} reported. Thank you!")


@router.get("/items/{item_id}", response_class=HTMLResponse)
def item_detail_page(
    request: Request,
    item_id: PositiveItemId,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    try:
        item, claim_count = crud.get_item_with_claim_count(session, item_id)
    except crud.ItemNotFoundError:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"message": f"Item {item_id} not found"},
            status_code=404,
        )

    return templates.TemplateResponse(
        request,
        "item_detail.html",
        {
            "item": item,
            "claim_count": claim_count,
            "errors": [],
            "form": {},
            "message": request.query_params.get("message"),
            "message_error": request.query_params.get("error") == "1",
        },
    )


@router.post("/items/{item_id}/claims")
def claim_submit(
    request: Request,
    item_id: PositiveItemId,
    claimant_name: str = Form(...),
    claimant_contact: str = Form(...),
    proof_description: str = Form(...),
    session: Session = Depends(get_session),
):
    form_data = {
        "claimant_name": claimant_name,
        "claimant_contact": claimant_contact,
        "proof_description": proof_description,
    }

    try:
        claim_data = ClaimCreate(
            claimant_name=claimant_name.strip(),
            claimant_contact=claimant_contact.strip(),
            proof_description=proof_description.strip(),
        )
    except ValidationError as exc:
        try:
            item, claim_count = crud.get_item_with_claim_count(session, item_id)
        except crud.ItemNotFoundError:
            return templates.TemplateResponse(
                request,
                "not_found.html",
                {"message": f"Item {item_id} not found"},
                status_code=404,
            )
        return templates.TemplateResponse(
            request,
            "item_detail.html",
            {
                "item": item,
                "claim_count": claim_count,
                "errors": _validation_messages(exc),
                "form": form_data,
            },
            status_code=422,
        )

    try:
        claim = crud.create_claim(session, item_id, claim_data)
    except crud.ItemNotFoundError:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"message": f"Item {item_id} not found"},
            status_code=404,
        )
    except crud.ItemNotOpenError as exc:
        return _flash_redirect(f"/items/{item_id}", str(exc), error=True)
    except crud.DomainError as exc:
        return _flash_redirect(f"/items/{item_id}", str(exc), error=True)

    return _flash_redirect(
        f"/items/{item_id}",
        f"Claim {claim.id} sent. Status: {claim.status}.",
    )
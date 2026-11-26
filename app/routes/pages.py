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
from app.schemas import UserCreate, ItemCreate, ClaimCreate, Category
from app.auth import BrowserUser, current_user
from app.accounts import EmailAlreadyRegisteredError, create_user, verify_password 
from app.sessions import SESSION_TTL, create_session, delete_session, SESSION_COOKIE

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

def _set_session_cookie(response: RedirectResponse, email: str) -> RedirectResponse:
    token = create_session(email)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=int(SESSION_TTL.total_seconds()),
        # secure=True  # enable when you serve over HTTPS
    )
    return response

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

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, user: BrowserUser | None = Depends(current_user)):
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "error": request.query_params.get("error"),
            "message": request.query_params.get("message"),
            "user": None,
        },
    )

@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    email = email.strip().lower()
    if not email.endswith("fhnw.ch"):
        return RedirectResponse(
            "/login?error=Please+use+your+%40fhnw.ch+email",
            status_code=303,
        )
    account = verify_password(session, email, password)
    if not account:
        return RedirectResponse(
            "/login?error=Incorrect+email+or+password",
            status_code=303,
        )
    response = RedirectResponse("/", status_code=303)
    return _set_session_cookie(response, account.email)

@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request, user: BrowserUser | None = Depends(current_user)):
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "error": request.query_params.get("error"),
            "form": {},
            "user": None,
        },
    )

@router.post("/register")
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    session: Session = Depends(get_session),
):
    form = {"email": email}
    if password != password_confirm:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "error": "Passwords do not match",
                "form": form,
                "user": None,
            },
            status_code=422,
        )

    try:
        data = UserCreate(email=email.strip().lower(), password=password)
    except ValidationError as exc:
        messages = _validation_messages(exc)
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "error": "; ".join(messages),
                "form": form,
                "user": None,
            },
            status_code=422,
        )

    try:
        user = create_user(session, data.email, data.password)
    except EmailAlreadyRegisteredError:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "error": "An account with this email already exists",
                "form": form,
                "user": None,
            },
            status_code=409,
        )

    response = RedirectResponse(
        "/?message=" + quote("Welcome! Your account was created."),
        status_code=303,
    )
    return _set_session_cookie(response, user.email)

@router.post("/logout")
def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    delete_session(token)
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response

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
            "user": current_user(request),
        },
    )

@router.get("/report", response_class=HTMLResponse)
def report_form(request: Request) -> HTMLResponse:
    user = current_user(request)
    form = {}
    if user:
        form["finder_contact"] = user.email
    
    return templates.TemplateResponse(
        request,
        "report_item.html",
        {
            "categories": CATEGORY_VALUES,
            "errors": [],
            "form": form,
            "today": date.today().isoformat(),
            "message": request.query_params.get("message"),
            "message_error": request.query_params.get("error") == "1",
            "user": user,
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
    user = current_user(request)
    form = {}
    if user:
        form["claimant_contact"] = user.email

    return templates.TemplateResponse(
        request,
        "item_detail.html",
        {
            "item": item,
            "claim_count": claim_count,
            "errors": [],
            "form": form,
            "message": request.query_params.get("message"),
            "message_error": request.query_params.get("error") == "1",
            "user": user,
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
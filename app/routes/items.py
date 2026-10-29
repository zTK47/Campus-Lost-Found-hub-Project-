from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlmodel import Session

from app import crud
from app.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.database import get_session
from app.models import ItemStatus
from app.schemas import (
    Category,
    ItemCreate,
    ItemDetail,
    ItemListResponse,
    ItemPublic,
    ItemUpdate,
)


router = APIRouter(prefix="/items", tags=["items"])
PositiveItemId = Annotated[int, Path(ge=1)]


@router.post("", response_model=ItemPublic, status_code=201)
def create_item(item: ItemCreate, session: Session = Depends(get_session)) -> ItemPublic:
    return crud.create_item(session, item)


@router.get("", response_model=ItemListResponse)
def list_items(
    q: str | None = None,
    category: Category | None = None,
    location: str | None = None,
    status: ItemStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: Session = Depends(get_session),
) -> ItemListResponse:
    items, count = crud.list_items(
        session,
        q=q,
        category=category,
        location=location,
        status=status,
        limit=limit,
        offset=offset,
    )
    return ItemListResponse(
        items=[ItemPublic.model_validate(item) for item in items],
        count=count,
        limit=limit,
        offset=offset,
    )


@router.get("/{item_id}", response_model=ItemDetail)
def get_item(item_id: PositiveItemId, session: Session = Depends(get_session)) -> ItemDetail:
    item, claim_count = crud.get_item_with_claim_count(session, item_id)
    public_item = ItemPublic.model_validate(item).model_dump()
    return ItemDetail.model_validate({**public_item, "claim_count": claim_count})


@router.patch("/{item_id}", response_model=ItemPublic)
def update_item(
    item_id: PositiveItemId,
    update: ItemUpdate,
    session: Session = Depends(get_session),
) -> ItemPublic:
    item = crud.update_item_status(session, item_id, update.status)
    return ItemPublic.model_validate(item)

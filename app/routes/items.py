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
    ErrorResponse,
    ItemCreate,
    ItemDetail,
    ItemListResponse,
    ItemPublic,
    ItemUpdate,
    ValidationErrorResponse,
)


router = APIRouter(prefix="/items", tags=["items"])
PositiveItemId = Annotated[int, Path(ge=1)]
ITEM_EXAMPLE = {
    "id": 12,
    "title": "Blue water bottle",
    "category": "bottle",
    "description": "Metal bottle with a sticker on the side.",
    "location_found": "Building A, lecture hall 2",
    "date_found": "2026-10-01",
    "status": "open",
    "created_at": "2026-11-08T14:58:43.316512Z",
}
VALIDATION_EXAMPLE = {
    "detail": [{
        "loc": ["body", "category"],
        "msg": "Input should be 'bottle', 'keys', 'clothing', 'electronics', 'id_card', 'bag' or 'other'",
        "type": "enum",
    }]
}


@router.post(
    "",
    response_model=ItemPublic,
    status_code=201,
    summary="Report a found item",
    description="Create an open found-item record without exposing finder contact.",
    responses={
        201: {"content": {"application/json": {"example": ITEM_EXAMPLE}}},
        422: {
            "model": ValidationErrorResponse,
            "description": "Validation error",
            "content": {"application/json": {"example": VALIDATION_EXAMPLE}},
        },
    },
)
def create_item(item: ItemCreate, session: Session = Depends(get_session)) -> ItemPublic:
    return crud.create_item(session, item)


@router.get(
    "",
    response_model=ItemListResponse,
    summary="List found items",
    description="Browse public found items with optional search and filters.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "items": [ITEM_EXAMPLE],
                        "count": 1,
                        "limit": 20,
                        "offset": 0,
                    }
                }
            }
        },
        422: {
            "model": ValidationErrorResponse,
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [{
                            "loc": ["query", "limit"],
                            "msg": "Input should be less than or equal to 100",
                            "type": "less_than_equal",
                        }]
                    }
                }
            },
        },
    },
)
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


@router.get(
    "/{item_id}",
    response_model=ItemDetail,
    summary="Get one found item",
    description="Return public item details and the number of claims.",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Item not found",
            "content": {"application/json": {"example": {"detail": "Item 999 not found"}}},
        },
        200: {"content": {"application/json": {"example": {**ITEM_EXAMPLE, "claim_count": 1}}}},
        422: {
            "model": ValidationErrorResponse,
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [{
                            "loc": ["path", "item_id"],
                            "msg": "Input should be greater than or equal to 1",
                            "type": "greater_than_equal",
                        }]
                    }
                }
            },
        },
    },
)
def get_item(item_id: PositiveItemId, session: Session = Depends(get_session)) -> ItemDetail:
    item, claim_count = crud.get_item_with_claim_count(session, item_id)
    public_item = ItemPublic.model_validate(item).model_dump()
    return ItemDetail.model_validate({**public_item, "claim_count": claim_count})


@router.patch(
    "/{item_id}",
    response_model=ItemPublic,
    summary="Update item status",
    description="Reopen or mark a claimed item as returned.",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Item not found",
            "content": {"application/json": {"example": {"detail": "Item 999 not found"}}},
        },
        409: {
            "model": ErrorResponse,
            "description": "Invalid status transition",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cannot change item 12 from open to claimed."
                    }
                }
            },
        },
        200: {"content": {"application/json": {"example": ITEM_EXAMPLE}}},
        422: {
            "model": ValidationErrorResponse,
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [{
                            "loc": ["body", "status"],
                            "msg": "Field required",
                            "type": "missing",
                        }]
                    }
                }
            },
        },
    },
)
def update_item(
    item_id: PositiveItemId,
    update: ItemUpdate,
    session: Session = Depends(get_session),
) -> ItemPublic:
    item = crud.update_item_status(session, item_id, update.status)
    return ItemPublic.model_validate(item)

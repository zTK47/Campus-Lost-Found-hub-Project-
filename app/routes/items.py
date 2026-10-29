from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app import crud
from app.database import get_session
from app.schemas import ItemCreate, ItemDetail, ItemPublic, ItemUpdate


router = APIRouter(prefix="/items", tags=["items"])
Category = Literal["bottle", "keys", "clothing", "electronics", "id_card", "bag", "other"]
Status = Literal["open", "claimed", "returned", "expired"]


@router.post("", response_model=ItemPublic, status_code=201)
def create_item(item: ItemCreate, session: Session = Depends(get_session)):
    return crud.create_item(session, item)


@router.get("")
def list_items(
    q: str | None = None,
    category: Category | None = None,
    location: str | None = None,
    status: Status | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: Session = Depends(get_session),
):
    items, count = crud.list_items(
        session, q=q, category=category, location=location, status=status, limit=limit, offset=offset
    )
    return {"items": [ItemPublic.model_validate(item) for item in items], "count": count, "limit": limit, "offset": offset}


@router.get("/{item_id}", response_model=ItemDetail)
def get_item(item_id: int, session: Session = Depends(get_session)):
    item = crud.get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    public_item = ItemPublic.model_validate(item).model_dump()
    return ItemDetail.model_validate({**public_item, "claim_count": len(item.claims)})


@router.patch("/{item_id}", response_model=ItemPublic)
def update_item(item_id: int, update: ItemUpdate, session: Session = Depends(get_session)):
    if update.status is None:
        raise HTTPException(status_code=409, detail="A status is required to update an item.")
    try:
        return crud.update_item_status(session, item_id, update.status)
    except crud.ItemNotFoundError:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    except crud.InvalidStatusTransitionError as error:
        raise HTTPException(status_code=409, detail=str(error))

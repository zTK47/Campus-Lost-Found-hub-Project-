from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.models import ClaimCreate, ClaimOut, ItemStatus
from app.db import items, claims, next_claim_id

router = APIRouter(tags=["claims"])

@router.post("/items/{item_id}/claims", response_model=ClaimOut, status_code=201)
def create_claim(item_id: int, claim: ClaimCreate):
    item = items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    if item.status != ItemStatus.open:
        raise HTTPException(
            status_code=409,
            detail=f"Item {item_id} is already {item.status.value} and cannot accept new claims.",
        )
    new_claim = ClaimOut(
        id=next_claim_id(),
        item_id=item_id,
        created_at=datetime.utcnow(),
        **claim.model_dump(),
    )
    claims[new_claim.id] = new_claim
    item.status = ItemStatus.claimed
    return new_claim
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlmodel import Session

from app import crud
from app.database import get_session
from app.schemas import ClaimCreate, ClaimFinder, ClaimPublic


router = APIRouter(tags=["claims"])
PositiveItemId = Annotated[int, Path(ge=1)]


@router.post("/items/{item_id}/claims", response_model=ClaimPublic, status_code=201)
def create_claim(
    item_id: PositiveItemId,
    claim: ClaimCreate,
    session: Session = Depends(get_session),
) -> ClaimPublic:
    return crud.create_claim(session, item_id, claim)


@router.get("/items/{item_id}/claims", response_model=list[ClaimFinder])
def list_claims(
    item_id: PositiveItemId,
    session: Session = Depends(get_session),
) -> list[ClaimFinder]:
    # TODO: require finder/admin authorization before exposing claimant contact and proof beyond the course demo.
    return crud.list_claims_for_item(session, item_id)

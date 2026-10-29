from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app import crud
from app.database import get_session
from app.schemas import ClaimCreate, ClaimFinder, ClaimPublic


router = APIRouter(tags=["claims"])


@router.post("/items/{item_id}/claims", response_model=ClaimPublic, status_code=201)
def create_claim(item_id: int, claim: ClaimCreate, session: Session = Depends(get_session)):
    try:
        return crud.create_claim(session, item_id, claim.model_dump())
    except crud.ItemNotFoundError:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    except crud.ClaimConflictError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.get("/items/{item_id}/claims", response_model=list[ClaimFinder])
def list_claims(item_id: int, session: Session = Depends(get_session)):
    # TODO: add finder authorization before exposing claimant contact and proof.
    try:
        return crud.list_claims_for_item(session, item_id)
    except crud.ItemNotFoundError:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

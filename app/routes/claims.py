from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlmodel import Session

from app import crud
from app.database import get_session
from app.schemas import ClaimCreate, ClaimDecision, ClaimFinder, ClaimPublic, ErrorResponse


router = APIRouter(tags=["claims"])
PositiveItemId = Annotated[int, Path(ge=1)]


@router.post(
    "/items/{item_id}/claims",
    response_model=ClaimPublic,
    status_code=201,
    summary="Submit an item claim",
    description="Create a pending claim while the item remains open.",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Item not found",
            "content": {"application/json": {"example": {"detail": "Item 999 not found"}}},
        },
        409: {
            "model": ErrorResponse,
            "description": "Item is not open",
            "content": {
                "application/json": {
                    "example": {
                        "detail": (
                            "Item 12 is claimed and cannot accept a claim decision."
                        )
                    }
                }
            },
        },
        422: {"description": "Validation error"},
    },
)
def create_claim(
    item_id: PositiveItemId,
    claim: ClaimCreate,
    session: Session = Depends(get_session),
) -> ClaimPublic:
    return crud.create_claim(session, item_id, claim)


@router.get(
    "/items/{item_id}/claims",
    response_model=list[ClaimFinder],
    summary="Review item claims",
    description=(
        "Return finder-only claim details, including proof. "
        "This endpoint currently has no authentication."
    ),
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Item not found",
            "content": {"application/json": {"example": {"detail": "Item 999 not found"}}},
        },
        422: {"description": "Validation error"},
    },
)
def list_claims(
    item_id: PositiveItemId,
    session: Session = Depends(get_session),
) -> list[ClaimFinder]:
    # TODO: require finder/admin authorization before exposing claimant contact and proof beyond the course demo.
    return crud.list_claims_for_item(session, item_id)


@router.patch(
    "/items/{item_id}/claims/{claim_id}",
    response_model=ClaimPublic,
    summary="Accept a claim",
    description="Accept one pending claim and reject the remaining pending claims.",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Claim not found",
            "content": {"application/json": {"example": {"detail": "Claim 999 not found"}}},
        },
        409: {
            "model": ErrorResponse,
            "description": "Claim cannot be accepted",
            "content": {
                "application/json": {
                    "example": {
                        "detail": (
                            "Item 12 is already claimed and cannot accept new claims."
                        )
                    }
                }
            },
        },
        422: {"description": "Validation error"},
    },
)
def accept_claim(
    item_id: PositiveItemId,
    claim_id: Annotated[int, Path(ge=1)],
    decision: ClaimDecision,
    session: Session = Depends(get_session),
) -> ClaimPublic:
    # TODO: require finder/admin authorization before accepting claims.
    return crud.accept_claim(session, item_id, claim_id)

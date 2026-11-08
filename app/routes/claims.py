from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlmodel import Session

from app import crud
from app.database import get_session
from app.schemas import (
    ClaimCreate,
    ClaimDecision,
    ClaimFinder,
    ClaimPublic,
    ErrorResponse,
    ValidationErrorResponse,
)

router = APIRouter(tags=["claims"])
PositiveItemId = Annotated[int, Path(ge=1)]
CLAIM_EXAMPLE = {
    "id": 1,
    "item_id": 12,
    "claimant_name": "Alex Example",
    "claimant_contact": "alex@example.com",
    "status": "pending",
    "created_at": "2026-11-08T15:01:49.191598Z",
}
CLAIM_FINDER_EXAMPLE = {
    **CLAIM_EXAMPLE,
    "proof_description": (
        "The sticker shows a mountain and there is a dent near the lid."
    ),
}
CLAIM_VALIDATION_EXAMPLE = {
    "detail": [{
        "loc": ["body", "proof_description"],
        "msg": "Field required",
        "type": "missing",
    }]
}


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
                            "Item 12 is already claimed and cannot accept new claims."
                        )
                    }
                }
            },
        },
        201: {"content": {"application/json": {"example": CLAIM_EXAMPLE}}},
        422: {
            "model": ValidationErrorResponse,
            "description": "Validation error",
            "content": {"application/json": {"example": CLAIM_VALIDATION_EXAMPLE}},
        },
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
        200: {
            "content": {
                "application/json": {"example": [CLAIM_FINDER_EXAMPLE]}
            }
        },
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
                    "examples": {
                        "item_not_open": {
                            "summary": "Item is not open",
                            "value": {
                                "detail": (
                                    "Item 12 is claimed and cannot accept a claim decision."
                                )
                            },
                        },
                        "claim_not_pending": {
                            "summary": "Claim is not pending",
                            "value": {
                                "detail": (
                                    "Claim 3 is already rejected and cannot be accepted."
                                )
                            },
                        },
                    }
                }
            },
        },
        200: {
            "content": {
                "application/json": {
                    "example": {**CLAIM_EXAMPLE, "status": "accepted"}
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
                            "loc": ["body", "status"],
                            "msg": "Input should be <ClaimStatus.accepted: 'accepted'>",
                            "type": "literal_error",
                        }]
                    }
                }
            },
        },
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

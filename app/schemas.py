from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.config import CATEGORY_VALUES
from app.models import ClaimStatus, ItemStatus

Category = Enum(
    "Category",
    {category: category for category in CATEGORY_VALUES},
    type=str,
)


class ItemCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{
                "title": "Blue water bottle",
                "category": "bottle",
                "description": "Metal bottle with a sticker on the side.",
                "location_found": "Building A, lecture hall 2",
                "date_found": "2026-10-01",
                "finder_contact": "finder@example.com",
            }]
        },
    )

    title: str = Field(min_length=1, max_length=100)
    category: Category
    description: str | None = Field(default=None, max_length=1000)
    location_found: str = Field(min_length=1, max_length=150)
    date_found: date
    finder_contact: EmailStr

    @field_validator("date_found")
    @classmethod
    def date_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("date_found must not be in the future")
        return value


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class ItemPublic(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [{
                "id": 12,
                "title": "Blue water bottle",
                "category": "bottle",
                "description": "Metal bottle with a sticker on the side.",
                "location_found": "Building A, lecture hall 2",
                "date_found": "2026-10-01",
                "status": "open",
                "created_at": "2026-11-08T14:58:43.316512Z",
            }]
        },
    )

    id: int
    title: str
    category: str
    description: str | None
    location_found: str
    date_found: date
    status: str
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value)


class ItemDetail(ItemPublic):
    claim_count: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [{
                "id": 12,
                "title": "Blue water bottle",
                "category": "bottle",
                "description": "Metal bottle with a sticker on the side.",
                "location_found": "Building A, lecture hall 2",
                "date_found": "2026-10-01",
                "status": "open",
                "created_at": "2026-11-08T14:58:43.316512Z",
                "claim_count": 1,
            }]
        },
    )


class ItemUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"status": "returned"}]},
    )

    status: ItemStatus


class ClaimCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{
                "claimant_name": "Alex Example",
                "claimant_contact": "alex@example.com",
                "proof_description": (
                    "The sticker shows a mountain and there is a dent near the lid."
                ),
            }]
        },
    )

    claimant_name: str = Field(min_length=1, max_length=100)
    claimant_contact: EmailStr
    proof_description: str = Field(min_length=1, max_length=2000)


class ClaimPublic(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [{
                "id": 1,
                "item_id": 12,
                "claimant_name": "Alex Example",
                "claimant_contact": "alex@example.com",
                "status": "pending",
                "created_at": "2026-11-08T15:01:49.191598Z",
            }]
        },
    )

    id: int
    item_id: int
    claimant_name: str
    claimant_contact: EmailStr
    status: str
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value)


class ClaimFinder(ClaimPublic):
    proof_description: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [{
                "id": 1,
                "item_id": 12,
                "claimant_name": "Alex Example",
                "claimant_contact": "alex@example.com",
                "status": "pending",
                "created_at": "2026-11-08T15:01:49.191598Z",
                "proof_description": (
                    "The sticker shows a mountain and there is a dent near the lid."
                ),
            }]
        },
    )


class ClaimDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal[ClaimStatus.accepted]


class ItemListResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "items": [{
                    "id": 12,
                    "title": "Blue water bottle",
                    "category": "bottle",
                    "description": "Metal bottle with a sticker on the side.",
                    "location_found": "Building A, lecture hall 2",
                    "date_found": "2026-10-01",
                    "status": "open",
                    "created_at": "2026-11-08T14:58:43.316512Z",
                }],
                "count": 1,
                "limit": 20,
                "offset": 0,
            }]
        },
    )

    items: list[ItemPublic]
    count: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    detail: str


class ValidationErrorDetail(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ValidationErrorResponse(BaseModel):
    detail: list[ValidationErrorDetail]

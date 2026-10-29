from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.config import CATEGORY_VALUES
from app.models import ItemStatus


Category = Enum(
    "Category",
    {category: category for category in CATEGORY_VALUES},
    type=str,
)


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    category: Category
    description: str | None = None
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
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ItemStatus | None = None


class ClaimCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claimant_name: str = Field(min_length=1, max_length=100)
    claimant_contact: EmailStr
    proof_description: str = Field(min_length=1)


class ClaimPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    claimant_name: str
    claimant_contact: EmailStr
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value)


class ClaimFinder(ClaimPublic):
    proof_description: str


class ItemListResponse(BaseModel):
    items: list[ItemPublic]
    count: int
    limit: int
    offset: int

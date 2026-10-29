from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


CATEGORIES = ("bottle", "keys", "clothing", "electronics", "id_card", "bag", "other")
StatusValue = Literal["open", "claimed", "returned", "expired"]


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    category: Literal["bottle", "keys", "clothing", "electronics", "id_card", "bag", "other"]
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


class ItemDetail(ItemPublic):
    claim_count: int


class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: StatusValue | None = None


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


class ClaimFinder(ClaimPublic):
    proof_description: str

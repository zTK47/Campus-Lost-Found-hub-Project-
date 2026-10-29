from datetime import date, datetime, timezone
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text


class ItemStatus(str, Enum):
    open = "open"
    claimed = "claimed"
    returned = "returned"
    expired = "expired"


class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(sa_column=Column(String(100), nullable=False))
    category: str = Field(sa_column=Column(String(30), nullable=False, index=True))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    location_found: str = Field(sa_column=Column(String(150), nullable=False))
    date_found: date = Field(sa_column=Column(Date, nullable=False))
    status: str = Field(
        default=ItemStatus.open.value,
        sa_column=Column(String(20), nullable=False, index=True),
    )
    finder_contact: str = Field(sa_column=Column(String(120), nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    claims: list["Claim"] = Relationship(back_populates="item")


class Claim(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    item_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("item.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    claimant_name: str = Field(sa_column=Column(String(100), nullable=False))
    claimant_contact: str = Field(sa_column=Column(String(120), nullable=False))
    proof_description: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    item: Item = Relationship(back_populates="claims")

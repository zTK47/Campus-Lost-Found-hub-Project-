from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class ItemStatus(str, Enum):
    open = "open"
    claimed = "claimed"
    returned = "returned"

class Item(BaseModel):
    id: int
    title: str
    category: str
    description: str | None = None
    location_found: str
    date_found: str
    status: ItemStatus = ItemStatus.open
    finder_contact: str

class ClaimCreate(BaseModel):
    claimant_name: str = Field(..., min_length=1)
    claimant_contact: str
    proof_description: str = Field(..., min_length=1)

class ClaimOut(ClaimCreate):
    id: int
    item_id: int
    created_at: datetime
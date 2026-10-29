from __future__ import annotations

from typing import Final

from sqlmodel import Session, func, select, update

from app.config import DEFAULT_PAGE_SIZE, DEFAULT_VISIBLE_STATUSES
from app.models import Claim, Item, ItemStatus
from app.schemas import ClaimCreate, Category, ItemCreate


class DomainError(Exception):
    """Base class for expected application rule failures."""


class ItemNotFoundError(DomainError):
    def __init__(self, item_id: int) -> None:
        super().__init__(f"Item {item_id} not found")


class InvalidStatusTransitionError(DomainError):
    def __init__(self, item_id: int, current: str, requested: str) -> None:
        super().__init__(f"Cannot change item {item_id} from {current} to {requested}.")


class MissingStatusError(DomainError):
    def __init__(self) -> None:
        super().__init__("A status is required to update an item.")


class ItemNotOpenError(DomainError):
    def __init__(self, item_id: int, status: str) -> None:
        super().__init__(
            f"Item {item_id} is already {status} and cannot accept new claims."
        )


ALLOWED_TRANSITIONS: Final[dict[ItemStatus, frozenset[ItemStatus]]] = {
    ItemStatus.open: frozenset({ItemStatus.claimed, ItemStatus.returned}),
    ItemStatus.claimed: frozenset({ItemStatus.open, ItemStatus.returned}),
    ItemStatus.returned: frozenset(),
}


def create_item(session: Session, item_data: ItemCreate) -> Item:
    item = Item(**item_data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def list_items(
    session: Session,
    *,
    q: str | None = None,
    category: Category | None = None,
    location: str | None = None,
    status: ItemStatus | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> tuple[list[Item], int]:
    statement = select(Item)
    count_statement = select(func.count()).select_from(Item)
    filters = []

    if q:
        pattern = f"%{q.lower()}%"
        filters.append(
            (func.lower(Item.title).like(pattern))
            | (func.lower(Item.description).like(pattern))
        )
    if category:
        filters.append(Item.category == category.value)
    if location:
        filters.append(func.lower(Item.location_found).like(f"%{location.lower()}%"))
    if status:
        filters.append(Item.status == status.value)
    else:
        filters.append(Item.status.in_(DEFAULT_VISIBLE_STATUSES))

    statement = statement.where(*filters).offset(offset).limit(limit)
    count_statement = count_statement.where(*filters)
    return list(session.exec(statement)), session.exec(count_statement).one()


def get_item(session: Session, item_id: int) -> Item:
    item = session.get(Item, item_id)
    if item is None:
        raise ItemNotFoundError(item_id)
    return item


def get_item_with_claim_count(session: Session, item_id: int) -> tuple[Item, int]:
    item = get_item(session, item_id)
    claim_count = session.exec(
        select(func.count()).select_from(Claim).where(Claim.item_id == item_id)
    ).one()
    return item, claim_count


def update_item_status(
    session: Session,
    item_id: int,
    new_status: ItemStatus | None,
) -> Item:
    if new_status is None:
        raise MissingStatusError

    item = get_item(session, item_id)
    try:
        current_status = ItemStatus(item.status)
    except ValueError as error:
        raise InvalidStatusTransitionError(item_id, item.status, new_status.value) from error

    if new_status not in ALLOWED_TRANSITIONS[current_status]:
        raise InvalidStatusTransitionError(item_id, current_status.value, new_status.value)

    item.status = new_status.value
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def create_claim(session: Session, item_id: int, claim_data: ClaimCreate) -> Claim:
    item = session.get(Item, item_id)
    if item is None:
        raise ItemNotFoundError(item_id)

    result = session.exec(
        update(Item)
        .where(Item.id == item_id, Item.status == ItemStatus.open.value)
        .values(status=ItemStatus.claimed.value)
    )
    if result.rowcount != 1:
        session.rollback()
        session.refresh(item)
        raise ItemNotOpenError(item_id, item.status)

    claim = Claim(item_id=item_id, **claim_data.model_dump())
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


def list_claims_for_item(session: Session, item_id: int) -> list[Claim]:
    get_item(session, item_id)
    return list(session.exec(select(Claim).where(Claim.item_id == item_id)))

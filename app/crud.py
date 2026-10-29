from sqlmodel import Session, func, select, update

from app.models import Claim, Item, ItemStatus
from app.schemas import ItemCreate


class ItemNotFoundError(Exception):
    pass


class InvalidStatusTransitionError(Exception):
    pass


class ClaimConflictError(Exception):
    pass


def create_item(session: Session, item_data: ItemCreate) -> Item:
    item = Item(**item_data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def list_items(
    session: Session,
    *,
    q: str | None,
    category: str | None,
    location: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Item], int]:
    statement = select(Item)
    count_statement = select(func.count()).select_from(Item)
    filters = []
    if q:
        pattern = f"%{q.lower()}%"
        filters.append((func.lower(Item.title).like(pattern)) | (func.lower(Item.description).like(pattern)))
    if category:
        filters.append(Item.category == category)
    if location:
        filters.append(func.lower(Item.location_found).like(f"%{location.lower()}%"))
    if status:
        filters.append(Item.status == status)
    else:
        filters.append(Item.status.in_([ItemStatus.open.value, ItemStatus.claimed.value]))
    statement = statement.where(*filters).offset(offset).limit(limit)
    count_statement = count_statement.where(*filters)
    return list(session.exec(statement)), session.exec(count_statement).one()


def get_item(session: Session, item_id: int) -> Item | None:
    return session.get(Item, item_id)


def update_item_status(session: Session, item_id: int, new_status: str) -> Item:
    item = session.get(Item, item_id)
    if item is None:
        raise ItemNotFoundError
    allowed = {
        ItemStatus.claimed.value: {ItemStatus.returned.value, ItemStatus.open.value, ItemStatus.expired.value},
        ItemStatus.open.value: {ItemStatus.returned.value, ItemStatus.expired.value},
    }
    if new_status not in allowed.get(item.status, set()):
        raise InvalidStatusTransitionError(
            f"Cannot change item {item_id} from {item.status} to {new_status}."
        )
    item.status = new_status
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def create_claim(session: Session, item_id: int, claim_data: dict) -> Claim:
    item = session.get(Item, item_id)
    if item is None:
        raise ItemNotFoundError
    result = session.exec(
        update(Item)
        .where(Item.id == item_id, Item.status == ItemStatus.open.value)
        .values(status=ItemStatus.claimed.value)
    )
    if result.rowcount != 1:
        session.rollback()
        raise ClaimConflictError(
            f"Item {item_id} is already {item.status} and cannot accept new claims."
        )
    claim = Claim(item_id=item_id, **claim_data)
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


def list_claims_for_item(session: Session, item_id: int) -> list[Claim]:
    if session.get(Item, item_id) is None:
        raise ItemNotFoundError
    return list(session.exec(select(Claim).where(Claim.item_id == item_id)))

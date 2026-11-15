import json

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.database import DEMO_ITEMS_PATH, seed_demo_data
from app.models import Item, ItemStatus
from app.schemas import ItemCreate


def _entries() -> list[dict]:
    return json.loads(DEMO_ITEMS_PATH.read_text(encoding="utf-8"))


def test_demo_items_follow_the_api_rules():
    for entry in _entries():
        public_fields = {k: v for k, v in entry.items() if k not in {"id", "status"}}
        ItemCreate.model_validate(public_fields)
        assert ItemStatus(entry["status"]) in {ItemStatus.open, ItemStatus.returned}


def test_demo_items_are_loaded_once_into_an_empty_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_demo_data(session)
        seed_demo_data(session)
        items = session.exec(select(Item)).all()
        assert len(items) == len(_entries())
        assert session.get(Item, 12).title == "Blue water bottle"

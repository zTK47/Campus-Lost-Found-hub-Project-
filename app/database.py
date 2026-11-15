from __future__ import annotations

import json
from collections.abc import Generator
from datetime import date
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from app.config import database_url
from app.models import Item, ItemStatus

DEMO_ITEMS_PATH = Path(__file__).resolve().parent / "data" / "demo_items.json"

DATABASE_URL = database_url()
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
    pool_recycle=3600,
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def seed_sample_data(session: Session) -> None:
    if session.exec(select(Item)).first() is not None:
        return
    session.add(
        Item(
            id=12,
            title="Blue water bottle",
            category="bottle",
            description="Metal bottle with a sticker on the side.",
            location_found="Building A, lecture hall 2",
            date_found=date(2026, 10, 1),
            status=ItemStatus.open.value,
            finder_contact="finder@example.com",
        )
    )
    session.commit()


def seed_demo_data(session: Session, path: Path = DEMO_ITEMS_PATH) -> None:
    """Load the demo items from a JSON file into an empty database.

    Used when the app starts with DEBUG and SEED_SAMPLE_DATA enabled. The tests
    keep using seed_sample_data(), which creates only item 12.
    """
    if session.exec(select(Item)).first() is not None:
        return
    for entry in json.loads(path.read_text(encoding="utf-8")):
        # SQLModel table models do not validate input, so the date is converted here.
        session.add(Item(**{**entry, "date_found": date.fromisoformat(entry["date_found"])}))
    session.commit()

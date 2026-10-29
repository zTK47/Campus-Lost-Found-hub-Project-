import os
from datetime import date
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Item, ItemStatus


def _database_url() -> str:
    configured_url = os.getenv("DB_URL")
    if configured_url:
        return configured_url
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    name = os.getenv("DB_NAME", "campus_lost_found")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"


DATABASE_URL = _database_url()
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
    if session.exec(select(Item)).first() is None:
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

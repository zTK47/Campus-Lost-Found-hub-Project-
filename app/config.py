from __future__ import annotations

import os


CATEGORY_VALUES = (
    "bottle",
    "keys",
    "clothing",
    "electronics",
    "id_card",
    "bag",
    "other",
)
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100
DEFAULT_VISIBLE_STATUSES = ("open", "claimed")


def _env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


DEBUG = _env_flag("DEBUG")
SEED_SAMPLE_DATA = _env_flag("SEED_SAMPLE_DATA") and DEBUG


def database_url() -> str:
    return os.getenv("DB_URL", "sqlite:///./campus_lost_found.db")

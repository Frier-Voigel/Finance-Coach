"""SQLite database engine and session helpers (unified for Person A & B)."""
from __future__ import annotations

import os
from collections.abc import Iterator
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import Engine
from sqlmodel import SQLModel, Session, create_engine

load_dotenv()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return (and cache) the SQLAlchemy/SQLModel engine.

    Reads DATABASE_URL from the environment; defaults to sqlite:///./coach.db.
    """
    url = os.environ.get("DATABASE_URL", "sqlite:///./coach.db")
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            from sqlalchemy.pool import StaticPool
            kwargs["poolclass"] = StaticPool
    return create_engine(url, **kwargs)


# Module-level engine reference for compatibility
engine = get_engine()


def init_db() -> None:
    """Create all SQLModel tables if they do not already exist."""
    import shared.schema  # noqa: F401
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    """FastAPI session dependency."""
    with Session(get_engine()) as session:
        yield session

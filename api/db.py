"""Database engine and session dependency (skeleton shared by both people)."""
from __future__ import annotations

import os
from collections.abc import Iterator

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

from shared import schema  # noqa: F401  (registers the tables)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./coach.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

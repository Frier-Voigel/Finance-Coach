"""Shared FastAPI dependencies for Person B's routers."""
from __future__ import annotations

from datetime import date

from fastapi import Depends, Query
from sqlmodel import Session

from shared.db import get_session
from engine.planner.store import SqlStore


def get_store(session: Session = Depends(get_session)) -> SqlStore:
    return SqlStore(session)


def get_today(as_of: date | None = Query(default=None, description="Pretend today is this date (demo/synthetic data)")) -> date:
    return as_of or date.today()

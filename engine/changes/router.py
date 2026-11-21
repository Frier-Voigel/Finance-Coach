"""GET /changes: the 'What changed' feed (events are written by engine/changes/middleware.py)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from engine.changes import service
from shared.db import get_session

router = APIRouter(tags=["changes"])


@router.get("/changes")
def list_changes(limit: int = Query(30, ge=1, le=200), after_id: int | None = Query(default=None, ge=0),
                 session: Session = Depends(get_session)) -> list[dict]:
    """Newest first. `after_id` returns only events newer than that id (used by the UI to detect fresh changes)."""
    return service.list_changes(session, limit, after_id)

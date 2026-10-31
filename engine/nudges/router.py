"""B3 endpoints: /nudges."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from api.deps import get_store, get_today
from api.errors import ApiError
from engine.nudges import service

router = APIRouter(tags=["nudges"])


@router.get("/nudges")
def list_nudges(store=Depends(get_store), today: date = Depends(get_today)) -> list[dict]:
    return service.sync_nudges(store, today)


@router.post("/nudges/{nudge_id}/dismiss")
def dismiss_nudge(nudge_id: int, store=Depends(get_store)) -> dict:
    nudge = service.dismiss(store, nudge_id)
    if nudge is None:
        raise ApiError(404, "nudge_not_found", f"No nudge with id {nudge_id}.")
    return nudge

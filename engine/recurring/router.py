"""Skeleton router for Person A recurring payments and subscriptions."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from api.db import get_session
from api.errors import ApiError
from shared.schema import Recurring

router = APIRouter(tags=["recurring"])


@router.get("/recurring")
def list_recurring(session: Session = Depends(get_session)):
    """List recurring charges and subscriptions."""
    items = session.exec(select(Recurring)).all()
    return items


@router.post("/recurring/{recurring_id}/mark-unused")
def mark_recurring_unused(recurring_id: int, session: Session = Depends(get_session)):
    """Mark a subscription as unused."""
    sub = session.get(Recurring, recurring_id)
    if not sub:
        raise ApiError(404, "recurring_not_found", f"Subscription {recurring_id} not found")
    sub.status = "unused"
    session.commit()
    session.refresh(sub)
    return sub

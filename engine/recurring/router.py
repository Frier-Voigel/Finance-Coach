"""FastAPI router for recurring subscription detection (A4)."""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from shared.db import get_engine
from shared.schema import Recurring, Transaction
from engine.recurring.detector import detect_recurring

router = APIRouter(tags=["recurring"])


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def _session():
    with Session(get_engine()) as session:
        yield session


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/recurring")
def list_recurring(session: Session = Depends(_session)):
    """Detect and return recurring transactions, merged with user annotations."""
    txns: list[Transaction] = list(session.exec(select(Transaction)).all())
    detected = detect_recurring(txns)

    # Build lookup of user-annotated recurring rows by merchant
    db_rows: list[Recurring] = list(session.exec(select(Recurring)).all())
    overrides: dict[str, str] = {r.merchant: r.status for r in db_rows}

    for item in detected:
        merchant = item["merchant"]
        if merchant in overrides:
            item["status"] = overrides[merchant]

    return detected


@router.post("/recurring/{merchant_hash}/mark-unused", status_code=200)
def mark_unused(merchant_hash: str, session: Session = Depends(_session)):
    """Mark a recurring merchant as unused by its merchant hash.

    Creates or updates the ``Recurring`` row with ``status="unused"``.
    """
    txns: list[Transaction] = list(session.exec(select(Transaction)).all())
    detected = detect_recurring(txns)

    matched = next(
        (item for item in detected if item.get("merchant_hash") == merchant_hash),
        None,
    )
    if matched is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "No recurring item with that hash."},
        )

    merchant = matched["merchant"]

    # Upsert Recurring row
    existing = session.exec(
        select(Recurring).where(Recurring.merchant == merchant)
    ).first()

    if existing:
        existing.status = "unused"
        session.add(existing)
    else:
        row = Recurring(
            merchant=merchant,
            amount=matched["amount"],
            cadence=matched["cadence"],
            last_seen=matched["last_seen"],
            next_expected=matched.get("next_expected"),
            status="unused",
        )
        session.add(row)

    session.commit()
    return {"merchant": merchant, "status": "unused"}

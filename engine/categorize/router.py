"""FastAPI router: transactions (A2) and rules (A3)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from shared.db import get_engine
from shared.schema import Rule, Transaction
from engine.categorize.service import patch_transaction as _patch

router = APIRouter(tags=["categorize"])


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def _session():
    with Session(get_engine()) as session:
        yield session


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PatchBody(BaseModel):
    category: str


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@router.get("/transactions")
def list_transactions(
    category: Optional[str] = None,
    source: Optional[str] = None,
    merchant: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(_session),
):
    """Return transactions with optional filters."""
    stmt = select(Transaction)
    if category:
        stmt = stmt.where(Transaction.category == category)
    if source:
        stmt = stmt.where(Transaction.source == source)
    if merchant:
        stmt = stmt.where(Transaction.merchant == merchant)
    if from_date:
        stmt = stmt.where(Transaction.date >= from_date)
    if to_date:
        stmt = stmt.where(Transaction.date <= to_date)
    stmt = stmt.offset(offset).limit(limit)
    return list(session.exec(stmt).all())


@router.patch("/transactions/{txn_id}")
def update_transaction(
    txn_id: int,
    body: PatchBody,
    session: Session = Depends(_session),
):
    """User-correct a transaction category and propagate the rule."""
    try:
        return _patch(txn_id, body.category, session)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": str(exc)})


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

@router.get("/rules")
def list_rules(session: Session = Depends(_session)):
    """Return all categorisation rules."""
    return list(session.exec(select(Rule)).all())


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, session: Session = Depends(_session)):
    """Delete a rule by id."""
    rule: Rule | None = session.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": f"rule {rule_id} not found"})
    session.delete(rule)
    session.commit()

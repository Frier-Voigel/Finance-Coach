"""Skeleton router for Person A categorization and correction loop."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from api.db import get_session
from api.errors import ApiError
from shared.schema import Rule, Transaction

router = APIRouter(tags=["categorize"])


class CategoryPatch(BaseModel):
    category: str


@router.get("/transactions")
def list_transactions(
    category: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    """List transactions with optional category filter. Person A implementation."""
    query = select(Transaction).order_by(Transaction.date.desc())
    if category:
        query = query.where(Transaction.category == category)
    results = session.exec(query.limit(limit)).all()
    return results


@router.patch("/transactions/{transaction_id}")
def update_transaction_category(
    transaction_id: int,
    body: CategoryPatch,
    session: Session = Depends(get_session),
):
    """Update transaction category and trigger rule creation loop."""
    txn = session.get(Transaction, transaction_id)
    if not txn:
        raise ApiError(404, "transaction_not_found", f"Transaction {transaction_id} not found")

    old_category = txn.category
    new_category = body.category.strip().title()
    txn.category = new_category
    txn.category_source = "user"

    # Create pattern rule if merchant exists
    rule_created = False
    updated_count = 1
    if txn.merchant:
        rule = Rule(
            pattern=txn.merchant,
            match_type="merchant",
            category=new_category,
            created_from_txn_id=txn.id,
        )
        session.add(rule)
        rule_created = True

        # Retroactively update matching transactions where category wasn't set by user
        matches = session.exec(
            select(Transaction).where(
                Transaction.merchant == txn.merchant,
                Transaction.id != txn.id,
                Transaction.category_source != "user",
            )
        ).all()
        for m in matches:
            m.category = new_category
            m.category_source = "rule"
            updated_count += 1

    session.commit()
    session.refresh(txn)

    return {
        "updated": updated_count,
        "rule_created": rule_created,
        "transaction": txn,
    }


@router.get("/rules")
def list_rules(session: Session = Depends(get_session)):
    """List learned categorization rules."""
    rules = session.exec(select(Rule).order_by(Rule.created_at.desc())).all()
    return rules


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, session: Session = Depends(get_session)):
    """Delete a learned rule."""
    rule = session.get(Rule, rule_id)
    if not rule:
        raise ApiError(404, "rule_not_found", f"Rule {rule_id} not found")
    session.delete(rule)
    session.commit()
    return {"deleted": True}

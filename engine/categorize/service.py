"""Service layer: persist ParsedTxns and handle the A3 correction loop."""
from __future__ import annotations

from typing import Callable

from sqlmodel import Session, select

from ingest.models import ParsedTxn
from shared.schema import Rule, Transaction
from engine.categorize.rules import categorize


def save_parsed_txns(
    txns: list[ParsedTxn],
    session: Session,
    llm: Callable[[str], str] | None = None,
) -> list[Transaction]:
    """Persist *txns* to the DB, auto-categorising each one.

    Parameters
    ----------
    txns:
        Normalised transactions from any ingest parser.
    session:
        Active SQLModel ``Session``; caller controls commit.
    llm:
        Optional callable (``prompt -> response``) for LLM fallback.

    Returns
    -------
    list[Transaction]
        The saved ORM objects (ids populated after ``session.commit``).
    """
    db_rules: list[Rule] = list(session.exec(select(Rule)).all())
    saved: list[Transaction] = []
    for p in txns:
        cat, source = categorize(p.merchant, p.description, db_rules, llm)
        txn = Transaction(
            date=p.date,
            amount=p.amount,
            direction=p.direction,
            description=p.description,
            merchant=p.merchant,
            category=cat,
            category_source=source,
            source=p.source,
            raw_text=p.raw_text,
            account=p.account,
        )
        session.add(txn)
        saved.append(txn)
    session.commit()
    for t in saved:
        session.refresh(t)
    return saved


def patch_transaction(txn_id: int, new_category: str, session: Session) -> dict:
    """Correction loop: update one transaction and propagate the rule.

    Steps
    -----
    1. Update the target transaction: ``category = new_category``,
       ``category_source = "user"``.
    2. Create a ``Rule`` (merchant exact-match) for that merchant.
    3. Re-apply the rule to all non-user transactions with the same merchant.

    Returns
    -------
    dict
        ``{"transaction": ..., "rule_created": ..., "past_updated": count}``
    """
    txn: Transaction | None = session.get(Transaction, txn_id)
    if txn is None:
        raise KeyError(f"transaction {txn_id} not found")

    # Step 1 – update the patched transaction
    txn.category = new_category
    txn.category_source = "user"
    session.add(txn)

    # Step 2 – create rule
    rule = Rule(
        pattern=txn.merchant,
        match_type="merchant",
        category=new_category,
        created_from_txn_id=txn_id,
    )
    session.add(rule)
    session.commit()
    session.refresh(txn)
    session.refresh(rule)
    rule_dict = rule.model_dump()
    txn_dict = txn.model_dump()

    # Step 3 – back-fill matching non-user transactions
    stmt = select(Transaction).where(
        Transaction.merchant == txn.merchant,
        Transaction.category_source != "user",
        Transaction.id != txn_id,
    )
    past: list[Transaction] = list(session.exec(stmt).all())
    for t in past:
        t.category = new_category
        t.category_source = "rule"
        session.add(t)
    session.commit()

    return {
        "transaction": txn_dict,
        "rule_created": rule_dict,
        "past_updated": len(past),
    }

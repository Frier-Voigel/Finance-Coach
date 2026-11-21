"""Subscription review use-cases. Reuses A's detector via engine.recurring.router (read-only, plus A's own mark-unused)."""
from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from engine.planner.service import load_profile
from engine.planner.store import SqlStore
from engine.recurring.router import list_recurring, mark_unused
from engine.subreview.review import build_review
from shared.schema import Recurring, SubscriptionAnswer, Transaction


def _latest_amounts(session: Session) -> dict[str, int]:
    """Latest debit per merchant (the detector's own `amount` is the most common one, i.e. the OLD price after a hike)."""
    latest: dict[str, tuple] = {}
    for t in session.exec(select(Transaction).where(Transaction.direction == "debit")):
        key = (t.date, t.id or 0)
        if t.merchant not in latest or key > latest[t.merchant][0]:
            latest[t.merchant] = (key, int(t.amount))
    return {m: v[1] for m, v in latest.items()}


def review(session: Session, today: date) -> dict:
    detected = list_recurring(session)
    amounts = _latest_amounts(session)
    subs = [{"merchant": d["merchant"], "merchant_hash": d["merchant_hash"], "cadence": d["cadence"], "status": d["status"],
             "amount": amounts.get(d["merchant"], int(d["amount"]))} for d in detected]
    answers = {a.merchant: {"answer": a.answer, "answered_on": a.answered_at.date()}
               for a in session.exec(select(SubscriptionAnswer))}
    return build_review(subs, load_profile(SqlStore(session))["monthly_income"], answers, today)


def answer(session: Session, merchant_hash: str, choice: str) -> str:
    """Store the user's answer; returns the merchant. Raises KeyError for an unknown hash.

    'not_using' reuses A's mark-unused so the Subscriptions page stays consistent. 'using' on something previously
    marked unused removes that override, so the detector's own status (e.g. 'changed') shows again.
    """
    match = next((d for d in list_recurring(session) if d["merchant_hash"] == merchant_hash), None)
    if match is None:
        raise KeyError(merchant_hash)
    merchant = match["merchant"]
    for old in session.exec(select(SubscriptionAnswer).where(SubscriptionAnswer.merchant == merchant)):
        session.delete(old)
    session.add(SubscriptionAnswer(merchant=merchant, answer=choice))
    session.commit()
    if choice == "not_using":
        mark_unused(merchant_hash, session)
    else:
        row = session.exec(select(Recurring).where(Recurring.merchant == merchant)).first()
        if row is not None and row.status == "unused":
            session.delete(row)
            session.commit()
    return merchant

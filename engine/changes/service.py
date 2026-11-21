"""'What changed' use-cases: snapshot the plan, diff two snapshots, persist and list events."""
from __future__ import annotations

import json
import os
import uuid
from datetime import date

from sqlmodel import Session, select

from engine.changes.diff import build_snapshot, diff_snapshots
from engine.planner.service import load_profile
from engine.planner.store import SqlStore
from engine.recurring.detector import detect_recurring  # A's engine, read-only use
from shared.schema import ChangeEvent, Recurring, Transaction


def resolve_today(as_of: str | None) -> date:
    """?as_of=... wins, then the AS_OF env var (demo date), then the real date."""
    raw = as_of or os.getenv("AS_OF") or ""
    try:
        return date.fromisoformat(raw) if raw else date.today()
    except ValueError:
        return date.today()


def _subscriptions(session: Session) -> list[dict]:
    """Detected subscriptions with their LATEST charge (detector's `amount` is the most common one, i.e. the old price)."""
    rows = list(session.exec(select(Transaction)).all())
    overrides = {r.merchant: r.status for r in session.exec(select(Recurring)).all()}
    out = []
    for d in detect_recurring(rows):
        debits = [t for t in rows if t.merchant == d["merchant"] and t.direction == "debit"]
        latest = max(debits, key=lambda t: (t.date, t.id or 0))
        out.append({"merchant": d["merchant"], "amount": int(latest.amount), "status": overrides.get(d["merchant"], d["status"])})
    return out


def current_snapshot(session: Session, today: date) -> dict:
    store = SqlStore(session)
    return build_snapshot(store.list_transactions(), load_profile(store), store.list_goals(), _subscriptions(session), today)


def record_change(session: Session, trigger: str, before: dict, after: dict) -> list[dict]:
    """Diff and store. Writes nothing (and returns []) when nothing moved."""
    events = diff_snapshots(before, after)
    if not events:
        return []
    batch = uuid.uuid4().hex[:12]
    rows = [ChangeEvent(batch_id=batch, trigger=trigger, kind=e["kind"], severity=e["severity"],
                        headline=e["headline"], data_json=json.dumps(e["data"])) for e in events]
    session.add_all(rows)
    session.commit()
    return [_row(r) for r in rows]


def _row(r: ChangeEvent) -> dict:
    return {"id": r.id, "batch_id": r.batch_id, "created_at": r.created_at, "trigger": r.trigger, "kind": r.kind,
            "severity": r.severity, "headline": r.headline, "data": json.loads(r.data_json)}


def list_changes(session: Session, limit: int = 30, after_id: int | None = None) -> list[dict]:
    """Newest first."""
    stmt = select(ChangeEvent).order_by(ChangeEvent.id.desc()).limit(limit)
    if after_id is not None:
        stmt = stmt.where(ChangeEvent.id > after_id)
    return [_row(r) for r in session.exec(stmt)]

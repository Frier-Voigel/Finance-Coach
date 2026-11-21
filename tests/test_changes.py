"""'What changed' feed: pure diff tests always run; the HTTP test is skipped without fastapi/sqlmodel."""
from datetime import date

import pytest

from engine.changes.diff import build_snapshot, diff_snapshots

TODAY = date(2026, 10, 15)
PROFILE = {"monthly_income": 75000, "fixed_costs": {"Rent": 24000}, "emergency_fund_current": 0, "emergency_fund_target": 0}
GOALS = [{"id": 1, "name": "Goa trip", "target_amount": 400000, "current_amount": 10000, "target_date": date(2028, 1, 1), "priority": 1}]


def _t(i, d, amt, cat, merchant="M"):
    return {"id": i, "date": d, "amount": amt, "direction": "debit", "category": cat, "merchant": merchant, "description": merchant}


def _history():
    out, i = [], 0
    for m in (7, 8, 9):  # three full months of usual spend
        for cat, amt in (("Dining", 6000), ("Groceries", 8000), ("Rent", 24000)):
            i += 1
            out.append(_t(i, date(2026, m, 5), amt, cat))
    return out


def snap(txns, subs=()):
    return build_snapshot(txns, PROFILE, GOALS, list(subs), TODAY)


def test_no_change_means_no_events():
    assert diff_snapshots(snap(_history()), snap(_history())) == []


def test_upload_overspend_slips_goal_and_names_the_cause():
    before = snap(_history())
    after = snap(_history() + [_t(99, date(2026, 10, 12), 9000, "Dining")])
    events = diff_snapshots(before, after)
    goal = next(e for e in events if e["kind"] == "goal_shift")
    assert goal["data"]["months"] > 0
    assert "Dining" in goal["headline"] and "over pace" in goal["headline"]
    assert any(e["kind"] == "category_pace" for e in events)


def test_correction_between_categories_is_a_reclassification_only():
    h = _history()
    moved = [{**t, "category": "Groceries"} if t["id"] == 1 else t for t in h]  # a Dining txn -> Groceries
    events = diff_snapshots(snap(h), snap(moved))
    assert [e["kind"] for e in events] == ["reclassified"]
    assert events[0]["data"] == {"from": "Dining", "to": "Groceries", "amount": 6000}


def test_subscription_price_rise_and_new_subscription():
    old = [{"merchant": "Netflix", "amount": 649, "status": "active"}]
    new = [{"merchant": "Netflix", "amount": 799, "status": "changed"}, {"merchant": "Hotstar", "amount": 299, "status": "active"}]
    heads = [e["headline"] for e in diff_snapshots(snap(_history(), old), snap(_history(), new))]
    assert "Netflix price rose ₹649 to ₹799" in heads
    assert any("Hotstar" in h for h in heads)


def test_month_rollover_does_not_invent_goal_shifts():
    nov = build_snapshot(_history(), PROFILE, GOALS, [], date(2026, 11, 21))
    assert [e for e in diff_snapshots(snap(_history()), nov) if e["kind"] in ("goal_shift", "category_pace")] == []


def test_empty_database_snapshot_does_not_crash():
    s = build_snapshot([], {"monthly_income": 0, "fixed_costs": {}, "emergency_fund_current": 0, "emergency_fund_target": 0}, [], [], TODAY)
    assert diff_snapshots(s, s) == []


# ---- HTTP: middleware must observe without changing the response ---------------------------------
pytest.importorskip("fastapi")
pytest.importorskip("sqlmodel")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from api.main import app  # noqa: E402
from shared.db import get_session  # noqa: E402
from shared.schema import Profile, Transaction  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AS_OF", "2026-10-15")
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(Profile(monthly_income=75000, fixed_costs_json='{"Rent": 24000}'))
        for t in _history():
            s.add(Transaction(date=t["date"], amount=t["amount"], direction="debit", description="x", merchant=f"m{t['id']}", category=t["category"]))
        s.commit()

    def override():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_correction_creates_a_feed_entry_and_response_is_unchanged(client):
    assert client.get("/changes").json() == []
    r = client.patch("/transactions/1", json={"category": "Groceries"})
    assert r.status_code == 200 and "rule_created" in r.json()  # A's response untouched
    feed = client.get("/changes").json()
    assert feed and feed[0]["trigger"] == "correction" and feed[0]["kind"] == "reclassified"


def test_failed_request_records_nothing(client):
    assert client.patch("/transactions/9999", json={"category": "Food"}).status_code == 404
    assert client.get("/changes").json() == []

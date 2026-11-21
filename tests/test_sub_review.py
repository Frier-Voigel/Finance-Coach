"""Subscription review prompts: pure logic always runs; the HTTP tests skip without fastapi/sqlmodel."""
from datetime import date, datetime

import pytest

from engine.subreview.review import build_review

TODAY = date(2026, 10, 15)


def sub(m, amt, status="active", cadence="monthly"):
    return {"merchant": m, "merchant_hash": f"h-{m}", "cadence": cadence, "status": status, "amount": amt}


def test_two_streaming_services_overlap_and_yearly_share_of_income():
    r = build_review([sub("Netflix", 799), sub("Hotstar", 299), sub("Spotify", 119)], 60000, {}, TODAY)
    assert [o["merchants"] for o in r["overlaps"]] == [["Netflix", "Hotstar"]]
    assert r["total_yearly_cost"] == (799 + 299 + 119) * 12
    assert r["total_pct_of_income"] == round((799 + 299 + 119) * 12 / (60000 * 12) * 100, 1)
    first = r["items"][0]
    assert first["merchant"] == "Netflix" and first["overlaps_with"] == ["Hotstar"] and first["ask"]  # overlaps are asked first
    assert next(i for i in r["items"] if i["merchant"] == "Spotify")["overlaps_with"] == []  # music is not video


def test_one_service_per_group_is_not_an_overlap():
    assert build_review([sub("Netflix", 799), sub("Spotify", 119)], 60000, {}, TODAY)["overlaps"] == []


def test_zero_income_gives_no_percentage_and_no_crash():
    r = build_review([sub("Netflix", 799)], 0, {}, TODAY)
    assert r["total_pct_of_income"] is None and r["items"][0]["pct_of_income"] is None


def test_answers_stop_the_prompt_and_expire_after_90_days():
    fresh = {"Netflix": {"answer": "using", "answered_on": date(2026, 9, 1)}}
    old = {"Netflix": {"answer": "using", "answered_on": date(2026, 5, 1)}}
    assert build_review([sub("Netflix", 799)], 60000, fresh, TODAY)["items"][0]["ask"] is False
    assert build_review([sub("Netflix", 799)], 60000, old, TODAY)["items"][0]["ask"] is True


def test_not_using_counts_toward_potential_savings_without_double_counting():
    ans = {"Netflix": {"answer": "not_using", "answered_on": date(2026, 10, 1)}}
    r = build_review([sub("Netflix", 799, "unused"), sub("Spotify", 119)], 60000, ans, TODAY)
    assert r["potential_yearly_savings"] == 799 * 12  # Netflix once, even though it is both unused and answered


def test_yearly_and_weekly_cadences_and_cancelled_are_handled():
    r = build_review([sub("Cloud", 1300, cadence="yearly"), sub("Mag", 50, cadence="weekly"), sub("Old", 500, "cancelled")], 60000, {}, TODAY)
    assert {i["merchant"]: i["yearly_cost"] for i in r["items"]} == {"Cloud": 1300, "Mag": 2600}


def test_disclaimer_is_always_present():
    assert "can't see usage" in build_review([], 0, {}, TODAY)["disclaimer"]


# ---- HTTP ----------------------------------------------------------------------------------------------
pytest.importorskip("fastapi")
pytest.importorskip("sqlmodel")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from api.main import app  # noqa: E402
from shared.db import get_session  # noqa: E402
from shared.schema import Profile, Transaction  # noqa: E402


@pytest.fixture
def client():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(Profile(monthly_income=60000, fixed_costs_json="{}"))
        for m in (7, 8, 9):
            s.add(Transaction(date=date(2026, m, 5), amount=649 if m < 9 else 799, direction="debit", description="NETFLIX", merchant="Netflix", category="Subscriptions"))
            s.add(Transaction(date=date(2026, m, 9), amount=299, direction="debit", description="HOTSTAR", merchant="Hotstar", category="Subscriptions"))
        s.commit()

    def override():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_review_endpoint_flags_overlap_and_uses_latest_price(client):
    r = client.get("/subscriptions/review", params={"as_of": "2026-10-15"}).json()
    assert r["overlaps"] and set(r["overlaps"][0]["merchants"]) == {"Netflix", "Hotstar"}
    assert next(i for i in r["items"] if i["merchant"] == "Netflix")["amount"] == 799  # latest, not the old 649


def test_not_using_marks_unused_in_A_endpoint_and_using_restores_it(client):
    items = client.get("/subscriptions/review").json()["items"]
    h = next(i["merchant_hash"] for i in items if i["merchant"] == "Hotstar")
    r = client.post(f"/subscriptions/review/{h}/answer", json={"answer": "not_using"})
    assert r.status_code == 200 and r.json()["review"]["potential_yearly_savings"] == 299 * 12
    assert next(x for x in client.get("/recurring").json() if x["merchant"] == "Hotstar")["status"] == "unused"
    client.post(f"/subscriptions/review/{h}/answer", json={"answer": "using"})
    assert next(x for x in client.get("/recurring").json() if x["merchant"] == "Hotstar")["status"] != "unused"


def test_unknown_hash_is_404_with_contract_error_shape(client):
    r = client.post("/subscriptions/review/nope/answer", json={"answer": "using"})
    assert r.status_code == 404 and r.json()["error"] == "recurring_not_found"
    assert client.post("/subscriptions/review/nope/answer", json={"answer": "maybe"}).status_code == 422

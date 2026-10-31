"""End-to-end tests through FastAPI + SQLite. Skipped automatically if fastapi/sqlmodel are not installed."""
from datetime import date

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlmodel")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from api.db import get_session  # noqa: E402
from api.main import app  # noqa: E402
from shared.schema import Transaction  # noqa: E402

TODAY = "2026-10-15"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("WISPR_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        for m in (7, 8, 9):
            for cat, amt, day in (("Dining", 6000, 5), ("Groceries", 8000, 6), ("Rent", 18000, 1)):
                s.add(Transaction(date=date(2026, m, day), amount=amt, direction="debit", description=f"{cat} spend", category=cat))
        s.add(Transaction(date=date(2026, 10, 3), amount=6000, direction="debit", description="Dining spend", category="Dining"))
        s.commit()

    def override():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)  # no `with`: skips the startup hook that would create ./coach.db
    app.dependency_overrides.clear()


def test_profile_goals_whatif_flow(client):
    p = {"monthly_income": 60000, "fixed_costs": {"rent": 18000}, "emergency_fund_current": 0, "emergency_fund_target": 0}
    assert client.put("/profile", json=p).json()["monthly_income"] == 60000
    assert client.get("/profile").json()["fixed_costs"] == {"rent": 18000}

    g = client.post("/goals", json={"name": "Trip", "target_amount": 115000, "target_date": "2027-06-30"})
    assert g.status_code == 201 and g.json()["priority"] == 1
    assert client.patch(f"/goals/{g.json()['id']}", json={"current_amount": 5000}).json()["current_amount"] == 5000
    view = client.get("/goals", params={"as_of": TODAY}).json()
    assert view["goals"][0]["projection"]["name"] == "Trip" and view["surplus"] == 28000

    r = client.post("/whatif", params={"as_of": TODAY}, json={"kind": "category_pct", "category": "dining out", "pct": -30})
    assert r.status_code == 200 and r.json()["surplus_delta"] == 1800


def test_error_shapes(client):
    assert client.patch("/goals/999", json={"name": "x"}).json()["error"] == "goal_not_found"
    r = client.post("/whatif", json={"kind": "category_pct", "category": "yachts", "pct": -5})
    assert r.status_code == 422 and r.json()["error"] == "unknown_category"
    r = client.post("/whatif", json={"kind": "category_pct", "category": "x"})
    assert r.status_code == 422 and r.json()["error"] == "validation_error"
    assert client.get("/reports/2026-13").json()["error"] == "bad_month"
    assert client.post("/nudges/999/dismiss").status_code == 404


def test_nudges_and_report(client):
    client.put("/profile", json={"monthly_income": 60000, "fixed_costs": {"rent": 18000}})
    n = client.get("/nudges", params={"as_of": TODAY}).json()
    assert len(n) == 1 and "Dining" in n[0]["message"]
    assert len(client.get("/nudges", params={"as_of": TODAY}).json()) == 1
    assert client.post(f"/nudges/{n[0]['id']}/dismiss").json()["dismissed"] is True
    assert client.get("/nudges", params={"as_of": TODAY}).json() == []
    rep = client.get("/reports/2026-10", params={"as_of": TODAY}).json()
    assert rep["total_spent"] == 6000 and "not financial advice" in rep["footer"]
    html = client.get("/reports/2026-10", params={"format": "html", "as_of": TODAY})
    assert html.headers["content-type"].startswith("text/html") and "Monthly review" in html.text


def test_voice_confirm_flow_and_guardrail(client):
    cmd = client.post("/voice/command", json={"text": "I earn 70,000 a month"}).json()
    assert cmd["intents"][0]["type"] == "SET_PROFILE" and client.get("/profile").json()["monthly_income"] == 0
    assert client.post("/voice/confirm", json={"log_id": cmd["log_id"]}).json()["confirmed"] is True
    assert client.get("/profile").json()["monthly_income"] == 70000
    assert client.post("/voice/confirm", json={"log_id": cmd["log_id"]}).json()["error"] == "already_resolved"
    assert client.post("/voice/confirm", json={"log_id": 999}).status_code == 404
    blocked = client.post("/voice/command", json={"text": "which stock should I buy?"}).json()
    assert blocked["blocked"] and "can't recommend" in blocked["reply"]


def test_voice_token_falls_back_without_key_and_coach_guard(client):
    r = client.post("/voice/token")
    assert r.status_code == 503 and r.json()["error"] == "wispr_not_configured"
    assert client.post("/coach/ask", json={"question": "is Bitcoin good?"}).json()["blocked"] is True
    ok = client.post("/coach/ask", params={"as_of": TODAY}, json={"question": "how am I doing?"}).json()
    assert ok["blocked"] is False and ok["answer"].endswith("not financial advice.")

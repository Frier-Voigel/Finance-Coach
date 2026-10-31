"""A4 recurring detection tests."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from shared.schema import Transaction
from engine.recurring.detector import detect_recurring


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_monthly(merchant: str, amount: Decimal, months: int, start: date) -> list[Transaction]:
    """Generate *months* monthly transactions for *merchant*."""
    txns = []
    for i in range(months):
        d = date(start.year + (start.month + i - 1) // 12,
                 (start.month + i - 1) % 12 + 1,
                 start.day)
        txns.append(Transaction(
            date=d,
            amount=amount,
            direction="debit",
            description=f"ECOM {merchant}",
            merchant=merchant,
            category="Subscriptions",
            category_source="rule",
            source="csv",
        ))
    return txns


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_detect_monthly_subscriptions():
    """NETFLIX and SPOTIFY should both be detected as monthly/active."""
    start = date(2025, 4, 5)
    txns = (
        _make_monthly("NETFLIX", Decimal("649.00"), 6, start)
        + _make_monthly("SPOTIFY", Decimal("119.00"), 6, date(2025, 4, 7))
    )
    results = detect_recurring(txns)
    merchants = {r["merchant"] for r in results}

    assert "NETFLIX" in merchants, f"NETFLIX not found in {merchants}"
    assert "SPOTIFY" in merchants, f"SPOTIFY not found in {merchants}"

    for r in results:
        assert r["cadence"] == "monthly"
        assert r["status"] == "active"


def test_price_change_flagged():
    """NETFLIX with a price hike on the 6th month must have status='changed'."""
    start = date(2025, 4, 5)
    txns = _make_monthly("NETFLIX", Decimal("649.00"), 5, start)
    # Add the 6th at a higher price
    txns.append(Transaction(
        date=date(2025, 9, 5),
        amount=Decimal("799.00"),
        direction="debit",
        description="ECOM NETFLIX",
        merchant="NETFLIX",
        category="Subscriptions",
        category_source="rule",
        source="csv",
    ))

    results = detect_recurring(txns)
    netflix = next((r for r in results if r["merchant"] == "NETFLIX"), None)
    assert netflix is not None, "NETFLIX not detected"
    assert netflix["status"] == "changed", f"Expected 'changed', got {netflix['status']}"


def test_insufficient_occurrences_ignored():
    """Only 2 transactions should not be flagged as recurring."""
    txns = [
        Transaction(
            date=date(2025, 4, 5),
            amount=Decimal("649.00"),
            direction="debit",
            description="ECOM NETFLIX",
            merchant="NETFLIX",
            category="Subscriptions",
            category_source="rule",
            source="csv",
        ),
        Transaction(
            date=date(2025, 5, 5),
            amount=Decimal("649.00"),
            direction="debit",
            description="ECOM NETFLIX",
            merchant="NETFLIX",
            category="Subscriptions",
            category_source="rule",
            source="csv",
        ),
    ]
    results = detect_recurring(txns)
    assert not any(r["merchant"] == "NETFLIX" for r in results)


def test_mark_unused_endpoint():
    """HTTP endpoint should mark a merchant as unused."""
    import os

    # Force an in-memory SQLite URL via env, then clear the lru_cache so
    # get_engine() picks it up fresh for this test.
    os.environ["DATABASE_URL"] = "sqlite://"

    from shared import db as db_module
    db_module.get_engine.cache_clear()

    # Build the in-memory schema
    engine = db_module.get_engine()
    SQLModel.metadata.create_all(engine)

    try:
        # Populate with enough NETFLIX transactions to be detected
        start = date(2025, 4, 5)
        with Session(engine) as s:
            for t in _make_monthly("NETFLIX", Decimal("649.00"), 6, start):
                s.add(t)
            s.commit()

        from api.main import app
        client = TestClient(app, raise_server_exceptions=True)

        # Get recurring list to find merchant_hash
        resp = client.get("/recurring")
        assert resp.status_code == 200
        items = resp.json()
        netflix = next((i for i in items if i["merchant"] == "NETFLIX"), None)
        assert netflix is not None, f"NETFLIX not in recurring: {items}"

        merchant_hash = netflix["merchant_hash"]
        resp2 = client.post(f"/recurring/{merchant_hash}/mark-unused")
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "unused"

        # GET recurring should now reflect status=unused
        resp3 = client.get("/recurring")
        netflix2 = next((i for i in resp3.json() if i["merchant"] == "NETFLIX"), None)
        assert netflix2 is not None
        assert netflix2["status"] == "unused"
    finally:
        # Restore normal engine resolution
        db_module.get_engine.cache_clear()
        os.environ.pop("DATABASE_URL", None)

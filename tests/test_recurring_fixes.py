"""Regression tests: salary is not a subscription; a price hike that sticks must not hide the subscription."""
from datetime import date
from decimal import Decimal

from engine.recurring.detector import detect_recurring
from shared.schema import Transaction


def _series(merchant, amounts, direction="debit"):
    return [
        Transaction(date=date(2025 + (3 + i) // 12, (3 + i) % 12 + 1, 5), amount=Decimal(a), direction=direction,
                    description=merchant, merchant=merchant, category="x", category_source="rule", source="csv")
        for i, a in enumerate(amounts)
    ]


def _by_name(txns):
    return {r["merchant"]: r["status"] for r in detect_recurring(txns)}


def test_salary_credits_are_not_subscriptions():
    got = _by_name(_series("ACME TECHNOLOGIES", [60000] * 6, direction="credit") + _series("NETFLIX", [649] * 6))
    assert "ACME TECHNOLOGIES" not in got and got["NETFLIX"] == "active"


def test_price_hike_that_sticks_keeps_the_subscription():
    for amounts in ([649] * 5 + [799] * 2, [649] * 3 + [799] * 3, [649] * 3 + [799] * 5):
        assert "NETFLIX" in _by_name(_series("NETFLIX", amounts)), amounts


def test_recent_hike_is_changed_and_old_hike_is_active_again():
    assert _by_name(_series("NETFLIX", [649] * 5 + [799]))["NETFLIX"] == "changed"
    assert _by_name(_series("NETFLIX", [649] * 3 + [799] * 6))["NETFLIX"] == "active"


def test_erratic_amounts_are_still_not_a_subscription():
    assert "GROCER" not in _by_name(_series("GROCER", [500, 900, 450, 1200, 300, 800]))

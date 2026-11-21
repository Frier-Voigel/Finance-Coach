"""Regressions from the live demo: rent in subscriptions, repeating nudges, 'what is an index fund?'."""
from datetime import date, timedelta

from coach.education import explain
from coach.guardrails import guard, output_violates
from engine.nudges.service import dismiss, sync_nudges
from engine.recurring.detector import detect_recurring
from shared.schema import Transaction
from tests.fakes import MemoryStore
from tests.test_b_services import PROFILE, store, tx
from voice import service as voice

TODAY = date(2026, 10, 15)


def test_rent_is_not_a_subscription_but_netflix_is():
    rows = []
    for i in range(4):
        d = date(2026, 6 + i, 3)
        rows.append(Transaction(date=d, amount=18000, direction="debit", description="UPI rent", merchant="LANDLORD RAJESH", category="Rent"))
        rows.append(Transaction(date=d, amount=649, direction="debit", description="NETFLIX", merchant="NETFLIX", category="Subscriptions"))
    assert [r["merchant"] for r in detect_recurring(rows)] == ["NETFLIX"]


def test_nudges_do_not_pile_up_and_stay_dismissed_with_a_demo_date():
    s = store()
    s.txns.append(tx(900, date(2026, 10, 3), 6000, "Dining"))
    for _ in range(4):  # every page load syncs; the demo date differs from the wall clock
        opened = sync_nudges(s, TODAY)
    assert len(opened) == 1 and len(s.nudges) == 1
    dismiss(s, opened[0]["id"])
    assert sync_nudges(s, TODAY) == [] and len(s.nudges) == 1


def test_older_duplicates_are_hidden_and_dismissed_together():
    s = store()
    s.txns.append(tx(900, date(2026, 10, 3), 6000, "Dining"))
    msg = "Dining: ₹6,000 so far this month, about 435% above your usual pace (₹1,863)."
    for _ in range(3):  # what the live database holds: copies stamped with another month
        s.add_nudge({"type": "category_drift", "message": msg, "severity": "high"})
    assert len(sync_nudges(s, TODAY)) == 1
    dismiss(s, sync_nudges(s, TODAY)[0]["id"])
    assert sync_nudges(s, TODAY) == []


def test_money_terms_are_explained_but_status_questions_and_picks_are_not_hijacked():
    ans = explain("what is an index fund?")
    assert ans and "index" in ans.lower() and not output_violates(ans) and guard("what is an index fund?") is None
    assert voice.handle_command(store(), "what is an index fund?", TODAY)["reply"] == ans
    assert explain("what is my emergency fund target?") is None and explain("how am I doing?") is None
    assert guard("which index fund should I buy?") is not None
    assert all(not output_violates(a) for _, a in __import__("coach.education", fromlist=["GLOSSARY"]).GLOSSARY)

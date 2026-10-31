"""Synthetic data: deterministic and contains the cases SPEC/REQUIREMENTS call for."""
from datetime import date

from data.synthetic.generate import build, sms_text, write_files
from engine.nudges.service import sync_nudges
from tests.fakes import MemoryStore

AS_OF = date(2026, 10, 15)


def _store(d):
    return MemoryStore(txns=[{**t, "id": i + 1} for i, t in enumerate(d["transactions"])], profile=d["profile"])


def test_deterministic_and_no_future_rows():
    d = build(AS_OF)
    assert d == build(AS_OF)
    assert max(t["date"] for t in d["transactions"]) <= AS_OF


def test_demo_cases_present():
    d = build(AS_OF)
    rents = sorted({t["amount"] for t in d["transactions"] if t["category"] == "Rent"})
    assert rents == [22000, 24000]  # rent increase
    assert {r["status"] for r in d["recurring"]} == {"active", "changed", "unused"}
    netflix = {t["amount"] for t in d["transactions"] if t["merchant"] == "Netflix"}
    assert netflix == {649, 799}  # price hike


def test_dining_spike_triggers_drift_nudge():
    msgs = [n["message"] for n in sync_nudges(_store(build(AS_OF)), AS_OF)]
    assert any(m.startswith("Dining:") for m in msgs)


def test_files_written(tmp_path):
    d = build(AS_OF)
    write_files(d, str(tmp_path))
    assert {p.name for p in tmp_path.iterdir()} == {"bank_statement_a.csv", "bank_statement_b.csv", "sms_messages.txt", "profile_goals.json"}
    assert "debited from A/c XX1234" in sms_text(next(t for t in d["transactions"] if t["direction"] == "debit"))

import io
import json
from datetime import date

import pytest

from coach.guardrails import REDIRECT, asks_for_security_advice, guard, output_violates
from voice.intent import parse_amount, parse_command, parse_date
from voice.wispr import WisprNotConfigured, get_client_token, token_request

TODAY = date(2026, 10, 31)


@pytest.mark.parametrize("q", [
    "which stock should I buy?", "is Bitcoin good to buy", "Should I invest in Tesla", "best mutual funds for me",
    "what are the best index funds", "should I buy $AAPL", "is reliance worth buying",
])
def test_guard_blocks_security_picks(q):
    assert guard(q) == REDIRECT


@pytest.mark.parametrize("q", [
    "what is an index fund", "how does a mutual fund work", "explain compound interest",
    "how much can I invest each month", "should I buy a laptop",
])
def test_guard_allows_education_and_planning(q):
    assert not asks_for_security_advice(q)


def test_output_check():
    assert output_violates("You should buy Tesla now") and output_violates("Put your money in $NVDA")
    assert not output_violates("An index fund tracks a market index.")
    assert guard("how much can I save?", "I recommend Bitcoin") == REDIRECT


def test_amounts_and_dates():
    assert [parse_amount(x) for x in ("3 lakh", "60,000", "2k", "1.5 crore", "Rs. 450")] == [300000, 60000, 2000, 15000000, 450]
    assert parse_amount("hello") is None
    assert parse_date("by next June", TODAY) == date(2027, 6, 30)
    assert parse_date("by March 2028", TODAY) == date(2028, 3, 31)
    assert parse_date("by november", TODAY) == date(2026, 11, 30)
    assert parse_date("in 8 months", TODAY) == date(2027, 6, 30)
    assert parse_date("someday", TODAY) is None


def test_spec_example_sentence():
    got = parse_command("I earn 60,000 a month, rent is 18,000, I want a 3 lakh emergency fund by next June.", TODAY)
    assert [i["type"] for i in got] == ["SET_PROFILE", "SET_PROFILE", "SET_GOAL"]
    assert got[0]["params"]["monthly_income"] == 60000 and got[1]["params"]["fixed_costs"] == {"rent": 18000}
    assert got[2]["params"] == {"name": "emergency fund", "target_amount": 300000, "target_date": "2027-06-30"}


def test_what_if_commands():
    a = parse_command("What if I cut dining out by 30%?", TODAY)[0]
    assert a == {"type": "WHAT_IF", "params": {"kind": "category_pct", "category": "dining out", "pct": -30.0}}
    b = parse_command("what if my rent goes up 2,000", TODAY)[0]
    assert b["params"] == {"kind": "fixed_abs", "name": "rent", "delta": 2000}


def test_correction_log_status_unknown():
    assert parse_command("Mark Swiggy as Food", TODAY)[0]["params"] == {"merchant": "Swiggy", "category": "Food"}
    assert parse_command("that Swiggy one is food, not shopping", TODAY)[0]["params"]["category"] == "food"
    e = parse_command("spent 450 on dinner yesterday", TODAY)[0]["params"]
    assert e == {"amount": 450, "description": "dinner", "date": "2026-10-30"}
    assert parse_command("how am I doing?", TODAY)[0]["type"] == "ASK_STATUS"
    assert parse_command("blah", TODAY)[0]["type"] == "UNKNOWN"
    assert parse_command("blah", TODAY, llm=lambda t: [{"type": "ASK_STATUS", "params": {}}])[0]["type"] == "ASK_STATUS"


def test_token_request_and_client(monkeypatch):
    r = token_request("fl-abc", "u1")
    assert r.full_url.endswith("/generate_access_token") and r.get_header("Authorization") == "Bearer fl-abc"
    assert json.loads(r.data)["client_id"] == "u1"

    monkeypatch.delenv("WISPR_API_KEY", raising=False)
    with pytest.raises(WisprNotConfigured):
        get_client_token("u1")

    class Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass

    monkeypatch.setenv("WISPR_API_KEY", "fl-abc")
    out = get_client_token("u1", opener=lambda req, timeout: Resp(b'{"access_token":"jwt","expires_in":3600}'))
    assert out["access_token"] == "jwt" and out["ws_url"].startswith("wss://") and out["ws_url"].endswith("Bearer%20jwt")

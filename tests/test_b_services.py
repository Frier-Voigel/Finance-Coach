"""Service-level tests for Person B (in-memory store, no web framework or DB needed)."""
import urllib.error
from datetime import date

import pytest
from pydantic import ValidationError

from coach.explain import phrase, status_text, whatif_text, with_footer
from coach.guardrails import REDIRECT, guard
from engine.nudges.service import dismiss, sync_nudges
from engine.planner import service as planner
from engine.planner.models import GoalIn, ProfileIn, WhatIfRequest
from engine.reports.service import build_report
from tests.fakes import MemoryStore
from voice import service as voice
from voice.intent import parse_command
from voice.llm_intent import make_llm_parser, validate

TODAY = date(2026, 10, 15)
PROFILE = {"monthly_income": 60000, "fixed_costs": {"rent": 18000}, "emergency_fund_current": 0, "emergency_fund_target": 0}


def tx(i, d, amt, cat, merchant=None):
    return {"id": i, "date": d, "amount": amt, "direction": "debit", "category": cat, "merchant": merchant or cat, "description": f"{merchant or cat} payment"}


def store(**kw):
    txns, n = [], 100
    for m in (7, 8, 9):
        for cat, amt, day in (("Dining", 6000, 5), ("Groceries", 8000, 6), ("Rent", 18000, 1)):
            n += 1
            txns.append(tx(n, date(2026, m, day), amt, cat))
    txns.append(tx(1, date(2026, 9, 20), 450, "Shopping", "Swiggy"))
    return MemoryStore(txns=txns, profile=dict(PROFILE), **kw)


# ---- planner service / models
def test_overview_and_fuzzy_whatif():
    s = store(goals=[{"id": 1, "name": "Trip", "target_amount": 119000, "current_amount": 0, "target_date": None, "priority": 1}])
    o = planner.overview(s, TODAY)
    assert o["variable"] == {"Dining": 6000, "Groceries": 8000, "Shopping": 150} and o["surplus"] == 60000 - 18000 - 14150
    r = planner.run_what_if(s, {"kind": "category_pct", "category": "dining out", "pct": -30}, TODAY)  # 'dining out' finds 'Dining'
    assert r["surplus_delta"] == 1800
    with pytest.raises(ValueError):
        planner.run_what_if(s, {"kind": "category_pct", "category": "yachts", "pct": -30}, TODAY)


def test_goals_view_attaches_projection_and_emergency_not_doubled():
    s = store()
    s.profile |= {"emergency_fund_target": 100000}
    planner.add_goal(s, {"name": "Trip", "target_amount": 30000})
    v = planner.goals_view(s, TODAY)
    assert v["emergency_fund"]["name"] == "Emergency fund" and v["goals"][0]["projection"]["name"] == "Trip"
    planner.add_goal(s, {"name": "My emergency fund", "target_amount": 100000})  # explicit goal replaces the derived one
    assert planner.goals_view(s, TODAY)["emergency_fund"] is None


def test_goal_priority_defaults_to_last_and_profile_merge():
    s = store()
    a = planner.add_goal(s, {"name": "A", "target_amount": 10})
    b = planner.add_goal(s, {"name": "B", "target_amount": 10})
    assert (a["priority"], b["priority"]) == (1, 2)
    planner.merge_profile(s, {"fixed_costs": {"emi": 5000, "bad": None}})
    p = planner.load_profile(s)
    assert p["monthly_income"] == 60000 and p["fixed_costs"] == {"rent": 18000, "emi": 5000}


def test_request_models_validate():
    assert WhatIfRequest(kind="category_pct", category="dining", pct=-30).change() == {"kind": "category_pct", "category": "dining", "pct": -30.0}
    for bad in ({"kind": "category_pct", "category": "x"}, {"kind": "nope"}, {"kind": "fixed_abs", "delta": 5},
                {"kind": "category_pct", "category": "x", "pct": -150}):
        with pytest.raises(ValidationError):
            WhatIfRequest(**bad)
    with pytest.raises(ValidationError):
        GoalIn(name="x", target_amount=0)
    with pytest.raises(ValidationError):
        ProfileIn(monthly_income=1, fixed_costs={"rent": -1})


# ---- nudges and report
def test_nudge_sync_dedupes_keeps_dismissed_and_renews_next_month():
    s = store()
    s.txns.append(tx(900, date(2026, 10, 3), 6000, "Dining"))
    first = sync_nudges(s, TODAY)
    assert [n["message"].split(":")[0] for n in first] == ["Dining"]
    sync_nudges(s, TODAY)
    assert len(s.nudges) == 1  # same month, same category: updated, not duplicated
    dismiss(s, first[0]["id"])
    assert sync_nudges(s, TODAY) == [] and len(s.nudges) == 1  # dismissed stays dismissed
    assert dismiss(s, 12345) is None


def test_build_report_validates_month_and_saves():
    s = store()
    with pytest.raises(ValueError):
        build_report(s, "2026-13", TODAY)
    r = build_report(s, "2026-09", TODAY)
    assert r["total_spent"] == 6000 + 8000 + 18000 + 450 and s.reports["2026-09"] is r and r["nudges"] == []
    assert "not financial advice" in r["footer"] and r["subscriptions"] == []
    s.recurring = [{"merchant": "Netflix", "amount": 649, "cadence": "monthly", "status": "changed"},
                   {"merchant": "Gym", "amount": 12000, "cadence": "yearly", "status": "unused"},
                   {"merchant": "Old", "amount": 99, "cadence": "weekly", "status": "cancelled"}]
    r = build_report(s, "2026-09", TODAY)
    assert [x["monthly_cost"] for x in r["subscriptions"]] == [649, 1000] and r["subscriptions_monthly_total"] == 1649
    from engine.reports.report import render_html
    assert "Netflix" in render_html(r) and "(unused)" in render_html(r) and "Old" not in render_html(r)


# ---- voice flow
def test_command_writes_nothing_until_confirmed():
    s = store()
    out = voice.handle_command(s, "I earn 75,000 a month, I want a 50,000 trip fund by next June", TODAY)
    assert [c["type"] for c in out["intents"]] == ["SET_PROFILE", "SET_GOAL"] and all(c["writes"] for c in out["intents"])
    assert s.profile["monthly_income"] == 60000 and s.goals == []  # nothing written yet
    res = voice.confirm(s, out["log_id"], True, TODAY)
    assert res["confirmed"] and all(r["ok"] for r in res["results"])
    assert s.profile["monthly_income"] == 75000 and s.goals[0]["target_amount"] == 50000 and s.goals[0]["target_date"] == date(2027, 6, 30)
    with pytest.raises(ValueError):
        voice.confirm(s, out["log_id"], True, TODAY)  # edge: cannot be applied twice


def test_cancel_and_unknown_log():
    s = store()
    out = voice.handle_command(s, "spent 450 on dinner yesterday", TODAY)
    assert voice.confirm(s, out["log_id"], False, TODAY) == {"confirmed": False, "results": []}
    assert not [t for t in s.txns if t.get("source") == "voice"]
    assert voice.confirm(s, 999, True, TODAY) is None


def test_log_expense_uses_rule_and_voice_source():
    s = store()
    s.rules.append(("dinner", "Food"))
    out = voice.handle_command(s, "spent 450 on dinner yesterday", TODAY)
    voice.confirm(s, out["log_id"], True, TODAY)
    t = s.txns[-1]
    assert (t["amount"], t["category"], t["date"], t["source"]) == (450, "Food", date(2026, 10, 14), "voice")


def test_correct_category_calls_patch_with_latest_match_and_handles_stub():
    s = store()
    s.txns.append(tx(2, date(2026, 8, 1), 300, "Shopping", "Swiggy"))
    calls = []
    out = voice.handle_command(s, "Mark Swiggy as food", TODAY)
    res = voice.confirm(s, out["log_id"], True, TODAY, patch_txn=lambda i, c: calls.append((i, c)) or {"updated": 14})
    assert calls == [(1, "Food")] and res["results"][0]["ok"]  # id 1 is the Sept 20 one (latest)
    out = voice.handle_command(s, "Mark Zomato as food", TODAY)
    assert voice.confirm(s, out["log_id"], True, TODAY)["results"][0]["ok"] is False  # no match
    out = voice.handle_command(s, "Mark Swiggy as food", TODAY)
    stub = voice.confirm(s, out["log_id"], True, TODAY, patch_txn=lambda i, c: {"stub": True, "message": "not up yet"})
    assert stub["results"][0] == {"type": "CORRECT_CATEGORY", "ok": False, "message": "not up yet"}


def test_patch_http_stubs_when_a_is_missing():
    def refuse(req, timeout):
        raise urllib.error.URLError("down")

    def missing(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 404, "nf", {}, None)

    assert voice.patch_transaction_http(1, "Food", opener=refuse)["stub"]
    assert voice.patch_transaction_http(1, "Food", opener=missing)["stub"]


def test_read_only_intents_answer_immediately_and_guardrail_blocks():
    s = store()
    out = voice.handle_command(s, "What if I cut dining out by 30%?", TODAY)
    card = out["intents"][0]
    assert not card["writes"] and card["answer"]["ok"] and "1,800" in card["answer"]["message"]
    bad = voice.handle_command(s, "What if I cut yachts by 30%?", TODAY)["intents"][0]["answer"]
    assert bad["ok"] is False
    status = voice.handle_command(s, "how am I doing?", TODAY)["intents"][0]["answer"]
    assert status["ok"] and "surplus" in status["message"]
    blocked = voice.handle_command(s, "which stock should I buy?", TODAY)
    assert blocked["blocked"] and blocked["reply"] == REDIRECT and blocked["log_id"] is None and blocked["intents"] == []


# ---- LLM fallback and coach text
def test_llm_intent_validation_and_cache():
    good = '```json\n[{"type":"ASK_STATUS","params":{}},{"type":"HACK","params":{}},{"type":"SET_GOAL","params":{"name":"Bike","target_amount":9000,"evil":1,"target_date":null}}]\n```'
    assert validate(good) == [{"type": "ASK_STATUS", "params": {}}, {"type": "SET_GOAL", "params": {"name": "Bike", "target_amount": 9000}}]
    assert validate("not json") == [] and validate(None) == [] and validate('{"type":"ASK_STATUS"}') == []
    n = []
    parser = make_llm_parser(lambda p: n.append(1) or good)
    parser("hmm"), parser("hmm")
    assert len(n) == 1
    assert parse_command("gibberish", TODAY, llm=make_llm_parser(lambda p: "nope"))[0]["type"] == "UNKNOWN"


def test_phrase_rejects_invented_numbers_and_securities():
    facts = "Surplus is ₹28,000 a month."
    assert phrase(facts, llm=lambda p: "You keep about 28000 rupees monthly.") == "You keep about 28000 rupees monthly."
    assert phrase(facts, llm=lambda p: "You keep ₹30,000 monthly.") == facts  # new number -> deterministic text
    assert phrase(facts, llm=lambda p: "Buy Tesla with ₹28,000.") == facts
    assert phrase(facts, llm=lambda p: None) == facts and phrase(facts) == facts


def test_explainers_and_footer():
    s = store(goals=[{"id": 1, "name": "Trip", "target_amount": 115000, "current_amount": 0, "target_date": None, "priority": 1}])
    r = planner.run_what_if(s, {"kind": "category_pct", "category": "dining", "pct": -30}, TODAY)
    text = whatif_text(r)
    assert "₹27,850" in text and "₹29,650" in text and "Trip:" in text and "earlier" in text
    assert "Trip" in status_text(planner.overview(s, TODAY), [])
    assert with_footer("x").endswith("not financial advice.")


def test_guard_classifier_adds_a_layer_but_never_replaces_rules():
    assert guard("is Bitcoin good?") == REDIRECT
    assert guard("hmm what about that one", classifier=lambda t: True) == REDIRECT
    assert guard("how much can I save?", classifier=lambda t: False) is None
    def boom(t): raise RuntimeError
    assert guard("how much can I save?", classifier=boom) is None  # a broken LLM does not break the request
    assert guard("which stock should I buy?", classifier=boom) == REDIRECT

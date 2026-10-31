from datetime import date

import pytest

from engine.nudges.nudges import drift_nudges
from engine.planner.planner import avg_monthly_by_category, project_goals, what_if
from engine.reports.report import monthly_report, render_html

TODAY = date(2026, 10, 15)
PROFILE = {"monthly_income": 60000, "fixed_costs": {"rent": 18000}, "emergency_fund_current": 0, "emergency_fund_target": 0}


def t(d, amt, cat, direction="debit"):
    return {"date": d, "amount": amt, "direction": direction, "category": cat}


def history(dining=6000, groceries=8000):
    out = []
    for m in (7, 8, 9):
        out += [t(date(2026, m, 5), dining, "Dining"), t(date(2026, m, 6), groceries, "Groceries"), t(date(2026, m, 1), 18000, "Rent")]
    return out


def test_avg_excludes_fixed_and_current_month():
    h = history() + [t(date(2026, 10, 2), 99999, "Dining")]
    assert avg_monthly_by_category(h, TODAY, exclude=["rent"]) == {"Dining": 6000, "Groceries": 8000}


def test_goal_projection_and_unreachable():
    goals = [{"name": "Trip", "target_amount": 30000, "current_amount": 0, "target_date": date(2027, 6, 30), "priority": 1}]
    g = project_goals(goals, 10000, TODAY)[0]
    assert g["months_needed"] == 3 and g["projected_date"] == date(2027, 1, 15) and g["on_track"]
    assert project_goals(goals, 0, TODAY)[0]["projected_date"] is None  # edge: no surplus


def test_goals_funded_in_priority_order():
    goals = [{"name": "B", "target_amount": 20000, "current_amount": 0, "target_date": None, "priority": 2},
             {"name": "A", "target_amount": 20000, "current_amount": 0, "target_date": None, "priority": 1}]
    a, b = project_goals(goals, 10000, TODAY)
    assert (a["name"], a["months_needed"], b["projected_date"]) == ("A", 2, date(2027, 2, 15))


def test_what_if_cut_dining_30pct_moves_date_earlier():
    variable = avg_monthly_by_category(history(), TODAY, exclude=["rent"])  # 6000 + 8000
    goals = [{"name": "Trip", "target_amount": 119000, "current_amount": 0, "target_date": None, "priority": 1}]
    r = what_if(PROFILE, variable, goals, TODAY, {"kind": "category_pct", "category": "dining", "pct": -30})
    assert r["surplus_before"] == 60000 - 18000 - 14000 == 28000
    assert r["surplus_delta"] == 1800  # 30% of 6000
    assert (r["before"][0]["months_needed"], r["after"][0]["months_needed"]) == (5, 4)  # 119000/28000 -> 5, /29800 -> 4
    assert r["after"][0]["projected_date"] == date(2027, 2, 15) and r["after"][0]["months_saved"] == 1


def test_what_if_rent_up_and_errors():
    variable = {"Dining": 6000}
    r = what_if(PROFILE, variable, [], TODAY, {"kind": "fixed_abs", "name": "Rent", "delta": 2000})
    assert r["surplus_delta"] == -2000
    with pytest.raises(ValueError):
        what_if(PROFILE, variable, [], TODAY, {"kind": "category_pct", "category": "nope", "pct": -10})


def test_emergency_fund_becomes_top_goal():
    p = PROFILE | {"emergency_fund_target": 300000}
    r = what_if(p, {}, [], TODAY, {"kind": "income_abs", "delta": 0})
    assert r["before"][0]["name"] == "Emergency fund" and r["before"][0]["remaining"] == 300000


def test_drift_nudge_fires_and_ignores_small():
    h = history() + [t(date(2026, 10, 3), 6000, "Dining"), t(date(2026, 10, 4), 300, "Groceries")]
    n = drift_nudges(h, TODAY)
    assert [x["category"] for x in n] == ["Dining"] and "above your usual pace" in n[0]["message"]
    assert drift_nudges(history(), TODAY) == []  # nothing this month


def test_report_and_html_escape():
    h = history() + [t(date(2026, 10, 3), 7000, "<b>Dining</b>")]
    r = monthly_report(h, "2026-10", PROFILE, [], drift_nudges(h, TODAY))
    assert r["total_spent"] == 7000 and r["savings_rate_pct"] == 88
    html = render_html(r)
    assert "&lt;b&gt;" in html and "not financial advice" in html

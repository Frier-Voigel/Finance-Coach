"""Deterministic money math (Person B). Amounts are whole rupees (int). No LLM here."""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta


def _key(d: dict, name: str) -> str | None:
    """Case-insensitive key lookup; falls back to substring either way ('dining out' finds 'Dining')."""
    low = name.lower().strip()
    exact = next((k for k in d if k.lower() == low), None)
    if exact or not low:
        return exact
    return next((k for k in d if low in k.lower() or k.lower() in low), None)


def avg_monthly_by_category(txns: list[dict], today: date, months: int = 3, exclude=()) -> dict[str, int]:
    """Average monthly debit per category over the last `months` full months before today's month.

    txn = {"date": date, "amount": int, "direction": "debit"|"credit", "category": str}
    `exclude` = category names to skip (e.g. fixed costs such as rent, to avoid double counting).
    """
    start = today.replace(day=1) - relativedelta(months=months)
    end = today.replace(day=1)
    skip = {e.lower() for e in exclude}
    totals: dict[str, int] = defaultdict(int)
    seen: set[tuple[int, int]] = set()
    for t in txns:
        if t["direction"] != "debit" or not (start <= t["date"] < end) or t["category"].lower() in skip:
            continue
        totals[t["category"]] += t["amount"]
        seen.add((t["date"].year, t["date"].month))
    n = max(len(seen), 1)
    return {c: round(v / n) for c, v in totals.items()}


def monthly_surplus(income: int, fixed: dict[str, int], variable: dict[str, int]) -> int:
    return income - sum(fixed.values()) - sum(variable.values())


def emergency_goal(profile: dict, goals: list[dict] = ()) -> dict | None:
    """Turn the profile's emergency fund target into a top-priority goal.

    Skipped when the user already has an explicit goal with 'emergency' in its name (no double counting).
    """
    cur, tgt = profile.get("emergency_fund_current", 0), profile.get("emergency_fund_target", 0)
    if tgt <= cur or any("emergency" in g["name"].lower() for g in goals):
        return None
    return {"name": "Emergency fund", "target_amount": tgt, "current_amount": cur, "target_date": None, "priority": 0}


def project_goals(goals: list[dict], surplus: int, today: date) -> list[dict]:
    """Fund goals one after another (lowest priority number first) using the whole monthly surplus.

    goal = {"name", "target_amount", "current_amount", "target_date": date|None, "priority"}
    """
    out, elapsed = [], 0  # elapsed=None once a goal is unreachable (surplus <= 0)
    for g in sorted(goals, key=lambda g: g["priority"]):
        remaining = max(g["target_amount"] - g["current_amount"], 0)
        if remaining == 0:
            months, done = 0, today
        elif surplus <= 0 or elapsed is None:
            months, done, elapsed = None, None, None
        else:
            months = math.ceil(remaining / surplus)
            elapsed += months
            done = today + relativedelta(months=elapsed)
        td = g.get("target_date")
        left = max(1, (td.year - today.year) * 12 + td.month - today.month) if td else None
        out.append({
            "id": g.get("id"),
            "name": g["name"],
            "remaining": remaining,
            "months_needed": months,
            "projected_date": done,
            "target_date": td,
            "on_track": done is not None and (td is None or done <= td),
            "required_monthly": math.ceil(remaining / left) if left else None,
        })
    return out


def apply_change(income: int, fixed: dict, variable: dict, change: dict) -> tuple[int, dict, dict]:
    """change kinds: category_pct {category,pct} | category_abs {category,delta} | fixed_abs {name,delta} | income_abs {delta}."""
    fixed, variable = dict(fixed), dict(variable)
    kind = change["kind"]
    if kind in ("category_pct", "category_abs"):
        k = _key(variable, change["category"])
        if k is None:
            raise ValueError(f"unknown category: {change['category']}")
        variable[k] = (
            round(variable[k] * (1 + change["pct"] / 100)) if kind == "category_pct" else max(0, variable[k] + change["delta"])
        )
    elif kind == "fixed_abs":
        k = _key(fixed, change["name"]) or change["name"]
        fixed[k] = max(0, fixed.get(k, 0) + change["delta"])
    elif kind == "income_abs":
        income += change["delta"]
    else:
        raise ValueError(f"unknown change kind: {kind}")
    return income, fixed, variable


def what_if(profile: dict, variable: dict, goals: list[dict], today: date, change: dict) -> dict:
    """Before/after surplus and goal dates for a hypothetical change."""
    income, fixed = profile["monthly_income"], profile["fixed_costs"]
    eg = emergency_goal(profile, goals)
    all_goals = ([eg] if eg else []) + goals
    s0 = monthly_surplus(income, fixed, variable)
    i1, f1, v1 = apply_change(income, fixed, variable, change)
    s1 = monthly_surplus(i1, f1, v1)
    before, after = project_goals(all_goals, s0, today), project_goals(all_goals, s1, today)
    for b, a in zip(before, after, strict=True):
        a["months_saved"] = (b["projected_date"] and a["projected_date"] and
                             (b["projected_date"].year - a["projected_date"].year) * 12 +
                             b["projected_date"].month - a["projected_date"].month)
    return {"surplus_before": s0, "surplus_after": s1, "surplus_delta": s1 - s0, "before": before, "after": after}

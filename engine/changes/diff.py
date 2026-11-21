"""'What changed' feed core (pure functions, no DB, no LLM). Compares two plan snapshots.

Reuses planner.py / nudges.py math so every number matches the Goals, Nudges and Report pages.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date

from engine.planner.planner import avg_monthly_by_category, emergency_goal, monthly_surplus, project_goals

DRIFT_PCT, MIN_ABS = 20, 500  # same defaults as engine/nudges/nudges.py


def _months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + b.month - a.month


def build_snapshot(txns: list[dict], profile: dict, goals: list[dict], subs: list[dict], today: date) -> dict:
    """Everything the diff needs, JSON-safe. txns/profile/goals use the same dict shapes as SqlStore.

    'pace' = usual monthly spend + whatever overshoot (or undershoot) has happened so far this month,
    i.e. 'the rest of the month goes at your usual rate'. Goal dates are projected on that pace surplus.
    """
    fixed = profile["fixed_costs"]
    usual = avg_monthly_by_category(txns, today, exclude=fixed)
    start = today.replace(day=1)
    mtd: dict[str, int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)
    for t in txns:
        if t["direction"] != "debit":
            continue
        totals[t["category"]] += t["amount"]
        if start <= t["date"] <= today and t["category"].lower() not in {f.lower() for f in fixed}:
            mtd[t["category"]] += t["amount"]
    frac = today.day / calendar.monthrange(today.year, today.month)[1]
    pace = {c: max(0, round(usual.get(c, 0) + mtd.get(c, 0) - usual.get(c, 0) * frac)) for c in {*usual, *mtd}}
    eg = emergency_goal(profile, goals)
    s_pace = monthly_surplus(profile["monthly_income"], fixed, pace)
    proj = project_goals(([eg] if eg else []) + goals, s_pace, today)
    over = {}
    for c, spent in mtd.items():
        exp = usual.get(c, 0) * frac
        if exp:
            over[c] = {"pct": round((spent / exp - 1) * 100), "amount": round(spent - exp), "spent": spent}
    return {
        "month": f"{today.year}-{today.month:02d}",
        "as_of": today.isoformat(),
        "txn_count": len(txns),
        "totals": dict(totals),
        "surplus_pace": s_pace,
        "goals": {p["name"]: {"months": p["months_needed"], "date": p["projected_date"].isoformat() if p["projected_date"] else None}
                  for p in proj},
        "over": over,
        "subs": {s["merchant"]: {"amount": s["amount"], "status": s["status"]} for s in subs},
    }


def _flagged(o: dict | None) -> bool:
    return bool(o) and o["pct"] >= DRIFT_PCT and o["amount"] >= MIN_ABS


def _cause(after: dict, before: dict) -> tuple[str, dict] | None:
    """The category whose overshoot grew the most between snapshots (the 'because')."""
    grew = [(c, o) for c, o in after["over"].items() if _flagged(o) and o["amount"] - before["over"].get(c, {"amount": 0})["amount"] > 0]
    return max(grew, key=lambda x: x[1]["amount"] - before["over"].get(x[0], {"amount": 0})["amount"], default=None)


def diff_snapshots(before: dict, after: dict) -> list[dict]:
    """Plain-language events, most important first. Same input -> same output."""
    ev: list[dict] = []
    same_month = before["month"] == after["month"]

    if same_month:
        cause = _cause(after, before)
        for name, a in after["goals"].items():
            b = before["goals"].get(name)
            if b is None or b["date"] == a["date"]:
                continue
            if a["date"] is None:
                head, shift = f"{name} is no longer reachable at this month's pace", None
            elif b["date"] is None:
                head, shift = f"{name} is reachable again, around {a['date'][:7]}", None
            else:
                shift = _months_between(date.fromisoformat(b["date"]), date.fromisoformat(a["date"]))
                if shift == 0:
                    continue
                head = f"{name} {'slipped' if shift > 0 else 'moved up'} {abs(shift)} month{'s' if abs(shift) != 1 else ''} at this month's pace"
            why = ""
            if cause and (shift is None or shift > 0):
                why = f" because {cause[0]} is {cause[1]['pct']}% over pace"
            ev.append({"kind": "goal_shift", "severity": "high" if (shift is None or shift > 0) else "good",
                       "headline": head + why, "data": {"goal": name, "before": b["date"], "after": a["date"], "months": shift}})

        for c in sorted({*before["over"], *after["over"]}):
            b, a = before["over"].get(c), after["over"].get(c)
            if _flagged(a) and (not _flagged(b) or abs(a["pct"] - b["pct"]) >= 10):
                ev.append({"kind": "category_pace", "severity": "medium",
                           "headline": f"{c} is {a['pct']}% over your usual pace (₹{a['amount']:,} ahead)",
                           "data": {"category": c, "pct": a["pct"], "amount": a["amount"]}})
            elif _flagged(b) and not _flagged(a):
                ev.append({"kind": "category_pace", "severity": "good", "headline": f"{c} is back within your usual pace",
                           "data": {"category": c}})

    if after["txn_count"] == before["txn_count"]:  # pure reclassification: money moved between categories
        moves = {c: after["totals"].get(c, 0) - before["totals"].get(c, 0) for c in {*before["totals"], *after["totals"]}}
        up = max(moves.items(), key=lambda x: x[1], default=(None, 0))
        down = min(moves.items(), key=lambda x: x[1], default=(None, 0))
        if up[1] > 0 and down[1] < 0:
            amt = min(up[1], -down[1])
            ev.append({"kind": "reclassified", "severity": "info", "headline": f"₹{amt:,} moved from {down[0]} to {up[0]}",
                       "data": {"from": down[0], "to": up[0], "amount": amt}})

    for m, a in sorted(after["subs"].items()):
        b = before["subs"].get(m)
        if b is None:
            ev.append({"kind": "subscription_new", "severity": "info", "headline": f"New subscription spotted: {m} ₹{a['amount']:,}/month",
                       "data": {"merchant": m, "amount": a["amount"]}})
        elif a["amount"] != b["amount"]:
            up = a["amount"] > b["amount"]
            ev.append({"kind": "subscription_price", "severity": "high" if up else "good",
                       "headline": f"{m} price {'rose' if up else 'dropped'} ₹{b['amount']:,} to ₹{a['amount']:,}",
                       "data": {"merchant": m, "before": b["amount"], "after": a["amount"]}})
        elif a["status"] != b["status"] and a["status"] == "unused":
            ev.append({"kind": "subscription_status", "severity": "info", "headline": f"{m} marked unused",
                       "data": {"merchant": m}})
    order = {"high": 0, "medium": 1, "good": 2, "info": 3}
    return sorted(ev, key=lambda e: order.get(e["severity"], 9))

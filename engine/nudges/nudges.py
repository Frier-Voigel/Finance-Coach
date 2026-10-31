"""Drift nudges (Person B): month-to-date spend vs the usual pace."""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date

from engine.planner.planner import avg_monthly_by_category


def drift_nudges(txns: list[dict], today: date, threshold: float = 0.2, min_abs: int = 500, exclude=()) -> list[dict]:
    """Flag categories whose month-to-date spend is `threshold` above the pro-rated trailing average.

    `min_abs` (rupees over pace) stops tiny categories from nagging.
    """
    month_start = today.replace(day=1)
    spent: dict[str, int] = defaultdict(int)
    for t in txns:
        if t["direction"] == "debit" and month_start <= t["date"] <= today:
            spent[t["category"]] += t["amount"]
    usual = avg_monthly_by_category(txns, today, exclude=exclude)
    frac = today.day / calendar.monthrange(today.year, today.month)[1]
    out = []
    for cat, s in spent.items():
        expected = usual.get(cat, 0) * frac
        if expected and s - expected >= min_abs and s > expected * (1 + threshold):
            pct = round((s / expected - 1) * 100)
            out.append({
                "type": "category_drift",
                "category": cat,
                "severity": "high" if s > expected * 1.5 else "medium",
                "message": f"{cat}: ₹{s:,} so far this month, about {pct}% above your usual pace (₹{round(expected):,}).",
            })
    return sorted(out, key=lambda n: n["severity"] != "high")

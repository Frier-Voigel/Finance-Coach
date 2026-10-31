"""Report use-case (Person B)."""
from __future__ import annotations

import re
from datetime import date

from engine.nudges.service import sync_nudges
from engine.planner.service import load_profile
from engine.reports.report import monthly_report

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def build_report(store, month: str, today: date) -> dict:
    """month = 'YYYY-MM' (ValueError if malformed). Open nudges are included only for the current month."""
    if not MONTH_RE.match(month):
        raise ValueError("month must look like 2026-10")
    nudges = sync_nudges(store, today) if month == f"{today.year}-{today.month:02d}" else []
    report = monthly_report(store.list_transactions(), month, load_profile(store), store.list_goals(),
                            [{k: n[k] for k in ("type", "message", "severity")} for n in nudges],
                            store.list_recurring())
    store.save_report(month, report)
    return report

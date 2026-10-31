"""Nudge use-cases (Person B): compute drift, keep one stored nudge per category per month."""
from __future__ import annotations

from datetime import date

from engine.nudges.nudges import drift_nudges
from engine.planner.service import load_profile


def computed_nudges(store, today: date) -> list[dict]:
    return drift_nudges(store.list_transactions(), today, exclude=load_profile(store)["fixed_costs"])


def sync_nudges(store, today: date) -> list[dict]:
    """Store new drift nudges, refresh the text of open ones, never resurrect a dismissed one. Returns open nudges."""
    existing = store.list_nudges(include_dismissed=True)
    for n in computed_nudges(store, today):
        prefix = f"{n['category']}:"
        match = next((e for e in existing if e["type"] == n["type"] and e["message"].startswith(prefix)
                      and (e["created_at"].year, e["created_at"].month) == (today.year, today.month)), None)
        if match is None:
            store.add_nudge({"type": n["type"], "message": n["message"], "severity": n["severity"]})
        elif not match["dismissed"]:
            store.update_nudge(match["id"], {"message": n["message"], "severity": n["severity"]})
    return sorted(store.list_nudges(), key=lambda n: n["severity"] != "high")


def dismiss(store, nudge_id: int) -> dict | None:
    return store.update_nudge(nudge_id, {"dismissed": True})

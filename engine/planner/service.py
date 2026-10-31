"""Planner use-cases over a store (Person B). All numbers come from planner.py; nothing here uses an LLM."""
from __future__ import annotations

from datetime import date

from engine.planner.planner import (
    avg_monthly_by_category,
    emergency_goal,
    monthly_surplus,
    project_goals,
    what_if,
)

EMPTY_PROFILE = {"monthly_income": 0, "fixed_costs": {}, "emergency_fund_current": 0, "emergency_fund_target": 0}


def load_profile(store) -> dict:
    return {**EMPTY_PROFILE, **(store.get_profile() or {})}


def save_profile(store, data: dict) -> dict:
    """Replace the profile (PUT semantics)."""
    return store.save_profile({k: data[k] for k in EMPTY_PROFILE})


def merge_profile(store, patch: dict) -> dict:
    """Voice SET_PROFILE: only the given fields change; fixed_costs entries are merged by name."""
    cur = load_profile(store)
    new = {**cur, **{k: v for k, v in patch.items() if k != "fixed_costs" and v is not None}}
    new["fixed_costs"] = {**cur["fixed_costs"], **{k: v for k, v in (patch.get("fixed_costs") or {}).items() if v is not None}}
    return save_profile(store, new)


def add_goal(store, data: dict) -> dict:
    """New goals go to the end of the priority order unless a priority is given."""
    if data.get("priority") is None:
        data = {**data, "priority": max((g["priority"] for g in store.list_goals()), default=0) + 1}
    return store.add_goal({"current_amount": 0, "target_date": None, **data})


def variable_spend(store, profile: dict, today: date) -> dict[str, int]:
    """Average monthly spend per category over the last 3 full months, minus the profile's fixed costs."""
    return avg_monthly_by_category(store.list_transactions(), today, exclude=profile["fixed_costs"])


def overview(store, today: date) -> dict:
    """Profile, usual variable spend, surplus and a projection for every goal (emergency fund first)."""
    profile = load_profile(store)
    variable = variable_spend(store, profile, today)
    surplus = monthly_surplus(profile["monthly_income"], profile["fixed_costs"], variable)
    goals = store.list_goals()
    eg = emergency_goal(profile, goals)
    projections = project_goals(([eg] if eg else []) + goals, surplus, today)
    return {"profile": profile, "variable": variable, "surplus": surplus, "projections": projections}


def goals_view(store, today: date) -> dict:
    """Stored goals, each with its projection; the profile-derived emergency fund is reported separately."""
    o = overview(store, today)
    by_id = {p["id"]: p for p in o["projections"] if p["id"] is not None}
    goals = [{**g, "projection": by_id.get(g["id"])} for g in store.list_goals()]
    emergency = next((p for p in o["projections"] if p["id"] is None), None)
    return {"surplus": o["surplus"], "goals": goals, "emergency_fund": emergency}


def run_what_if(store, change: dict, today: date) -> dict:
    """Raises ValueError for an unknown category/kind; the router turns that into a 422."""
    profile = load_profile(store)
    variable = variable_spend(store, profile, today)
    return what_if(profile, variable, store.list_goals(), today, change)

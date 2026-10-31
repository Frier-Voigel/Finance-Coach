"""Seed script to load synthetic transactions, profile, goals, and subscriptions into the DB.

Usage:
    python shared/seed.py          # generates fixtures if missing, then seeds database
    python shared/seed.py --fresh  # forces fresh synthetic data generation before seeding
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

# Ensure repository root is on Python module search path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from dotenv import load_dotenv

load_dotenv()

from sqlmodel import SQLModel, Session

from api.db import engine
from shared.schema import Goal, Nudge, Profile, Recurring, Transaction


def seed_database(data: dict) -> None:
    """Drop and recreate all tables, then insert initial dataset."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        # 1. Transactions
        txns = data.get("transactions", [])
        for t in txns:
            s.add(
                Transaction(
                    date=dt.date.fromisoformat(t["date"]),
                    amount=int(t["amount"]),
                    direction=t["direction"],
                    description=t["description"],
                    merchant=t.get("merchant"),
                    category=t.get("category"),
                    category_source="rule" if t.get("category") else None,
                    source=t.get("source", "csv"),
                    raw_text=t.get("raw_text"),
                )
            )

        # 2. Profile
        prof = data.get("profile", {})
        if prof:
            s.add(
                Profile(
                    monthly_income=int(prof.get("monthly_income", 0)),
                    fixed_costs_json=json.dumps(prof.get("fixed_costs", {})),
                    emergency_fund_current=int(prof.get("emergency_fund_current", 0)),
                    emergency_fund_target=int(prof.get("emergency_fund_target", 0)),
                )
            )

        # 3. Goals
        for g in data.get("goals", []):
            s.add(
                Goal(
                    name=g["name"],
                    target_amount=int(g["target_amount"]),
                    current_amount=int(g.get("current_amount", 0)),
                    target_date=dt.date.fromisoformat(g["target_date"]) if g.get("target_date") else None,
                    priority=int(g.get("priority", 1)),
                )
            )

        # 4. Recurring subscriptions
        for r in data.get("recurring", []):
            s.add(
                Recurring(
                    merchant=r["merchant"],
                    amount=int(r["amount"]),
                    cadence=r.get("cadence", "monthly"),
                    last_seen=dt.date.fromisoformat(r["last_seen"]) if r.get("last_seen") else None,
                    next_expected=dt.date.fromisoformat(r["next_expected"]) if r.get("next_expected") else None,
                    status=r.get("status", "active"),
                )
            )

        s.commit()

        print(
            f"Seeded: {len(txns)} transactions, "
            f"{'1 profile' if prof else '0 profile'}, "
            f"{len(data.get('goals', []))} goals, "
            f"{len(data.get('recurring', []))} recurring subscriptions."
        )


def main():
    force_fresh = "--fresh" in sys.argv
    fixture_path = os.path.join(REPO_ROOT, "data", "synthetic", "output", "seed_data.json")

    if force_fresh or not os.path.exists(fixture_path):
        print("Generating synthetic dataset...")
        from data.synthetic.generate import write_outputs
        write_outputs()

    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    print("Populating database with seed data...")
    seed_database(data)
    print("Database ready.")


if __name__ == "__main__":
    main()

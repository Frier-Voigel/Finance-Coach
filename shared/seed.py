"""Seed script to load synthetic transactions, profile, goals, and subscriptions into the DB.

Usage:
    python shared/seed.py          # generates fixtures if missing, then seeds database
    python shared/seed.py --fresh  # forces fresh synthetic data generation before seeding
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
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

from shared.db import get_engine
from shared.schema import Goal, Nudge, Profile, Recurring, Transaction


def _parse_date(val) -> dt.date | None:
    if val is None:
        return None
    if isinstance(val, dt.date):
        return val
    return dt.date.fromisoformat(str(val))


def seed_database(data: dict) -> None:
    """Drop and recreate all tables, then insert initial dataset."""
    engine = get_engine()
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        # 1. Transactions
        txns = data.get("transactions", [])
        for t in txns:
            s.add(
                Transaction(
                    date=_parse_date(t["date"]),
                    amount=Decimal(str(t["amount"])),
                    direction=t["direction"],
                    description=t["description"],
                    merchant=t.get("merchant", ""),
                    category=t.get("category", "Other"),
                    category_source="rule" if t.get("category") else None,
                    source=t.get("source", "csv"),
                    raw_text=t.get("raw_text", ""),
                )
            )

        # 2. Profile
        prof = data.get("profile", {})
        if prof:
            s.add(
                Profile(
                    monthly_income=Decimal(str(prof.get("monthly_income", 0))),
                    fixed_costs_json=json.dumps(prof.get("fixed_costs", {})),
                    emergency_fund_current=Decimal(str(prof.get("emergency_fund_current", 0))),
                    emergency_fund_target=Decimal(str(prof.get("emergency_fund_target", 0))),
                )
            )

        # 3. Goals
        for g in data.get("goals", []):
            s.add(
                Goal(
                    name=g["name"],
                    target_amount=Decimal(str(g["target_amount"])),
                    current_amount=Decimal(str(g.get("current_amount", 0))),
                    target_date=_parse_date(g.get("target_date")),
                    priority=int(g.get("priority", 1)),
                )
            )

        # 4. Recurring subscriptions
        for r in data.get("recurring", []):
            s.add(
                Recurring(
                    merchant=r["merchant"],
                    amount=Decimal(str(r["amount"])),
                    cadence=r.get("cadence", "monthly"),
                    last_seen=_parse_date(r.get("last_seen")),
                    next_expected=_parse_date(r.get("next_expected")),
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

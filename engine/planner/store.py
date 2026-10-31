"""SQLModel-backed store (Person B). Services only talk to this duck-typed interface, so they are testable
without a database (see tests/fakes.py::MemoryStore). Rows leave as plain dicts; amounts are whole rupees.
"""
from __future__ import annotations

import json
import re

from sqlmodel import Session, select

from shared.schema import utcnow
from shared.schema import Goal, Nudge, Profile, Recurring, Report, Rule, Transaction, VoiceLog


def _goal(g: Goal) -> dict:
    return {"id": g.id, "name": g.name, "target_amount": int(g.target_amount), "current_amount": int(g.current_amount),
            "target_date": g.target_date, "priority": g.priority}


def _txn(t: Transaction) -> dict:
    return {"id": t.id, "date": t.date, "amount": int(t.amount), "direction": t.direction, "category": t.category or "Uncategorized",
            "merchant": t.merchant, "description": t.description}


def _nudge(n: Nudge) -> dict:
    return {"id": n.id, "created_at": n.created_at, "type": n.type, "message": n.message, "severity": n.severity, "dismissed": n.dismissed}


class SqlStore:
    def __init__(self, session: Session):
        self.s = session

    # profile (single row)
    def get_profile(self) -> dict | None:
        p = self.s.exec(select(Profile)).first()
        if p is None:
            return None
        return {"monthly_income": int(p.monthly_income), "fixed_costs": json.loads(p.fixed_costs_json),
                "emergency_fund_current": int(p.emergency_fund_current), "emergency_fund_target": int(p.emergency_fund_target),
                "updated_at": p.updated_at}

    def save_profile(self, d: dict) -> dict:
        p = self.s.exec(select(Profile)).first() or Profile()
        p.monthly_income, p.fixed_costs_json = d["monthly_income"], json.dumps(d["fixed_costs"])
        p.emergency_fund_current, p.emergency_fund_target = d["emergency_fund_current"], d["emergency_fund_target"]
        p.updated_at = utcnow()
        self.s.add(p)
        self.s.commit()
        return self.get_profile()

    # goals
    def list_goals(self) -> list[dict]:
        return [_goal(g) for g in self.s.exec(select(Goal).order_by(Goal.priority, Goal.id))]

    def add_goal(self, d: dict) -> dict:
        g = Goal(**d)
        self.s.add(g)
        self.s.commit()
        self.s.refresh(g)
        return _goal(g)

    def update_goal(self, goal_id: int, patch: dict) -> dict | None:
        g = self.s.get(Goal, goal_id)
        if g is None:
            return None
        for k, v in patch.items():
            setattr(g, k, v)
        self.s.add(g)
        self.s.commit()
        self.s.refresh(g)
        return _goal(g)

    # transactions (owned by A; B reads, and inserts voice-logged expenses)
    def list_transactions(self) -> list[dict]:
        return [_txn(t) for t in self.s.exec(select(Transaction))]

    def find_transactions(self, text: str) -> list[dict]:
        """Most recent first; matches merchant or description, case-insensitive."""
        low = text.lower().strip()
        hits = [t for t in self.s.exec(select(Transaction))
                if low and (low in (t.merchant or "").lower() or low in t.description.lower())]
        return [_txn(t) for t in sorted(hits, key=lambda t: (t.date, t.id or 0), reverse=True)]

    def add_transaction(self, d: dict) -> dict:
        t = Transaction(**d)
        self.s.add(t)
        self.s.commit()
        self.s.refresh(t)
        return _txn(t)

    def rule_category(self, description: str) -> str | None:
        """First of A's saved rules that matches this description (read-only)."""
        low = description.lower()
        for r in self.s.exec(select(Rule)):
            if r.match_type == "regex":
                if re.search(r.pattern, description, re.I):
                    return r.category
            elif r.pattern.lower() in low:
                return r.category
        return None

    def list_recurring(self) -> list[dict]:
        """Subscriptions detected by A's engine (read-only)."""
        return [{"merchant": r.merchant, "amount": int(r.amount), "cadence": r.cadence, "status": r.status}
                for r in self.s.exec(select(Recurring))]

    # nudges
    def list_nudges(self, include_dismissed: bool = False) -> list[dict]:
        rows = self.s.exec(select(Nudge).order_by(Nudge.id.desc()))
        return [_nudge(n) for n in rows if include_dismissed or not n.dismissed]

    def add_nudge(self, d: dict) -> dict:
        n = Nudge(**d)
        self.s.add(n)
        self.s.commit()
        self.s.refresh(n)
        return _nudge(n)

    def update_nudge(self, nudge_id: int, fields: dict) -> dict | None:
        n = self.s.get(Nudge, nudge_id)
        if n is None:
            return None
        for k, v in fields.items():
            setattr(n, k, v)
        self.s.add(n)
        self.s.commit()
        self.s.refresh(n)
        return _nudge(n)

    # reports
    def save_report(self, month: str, payload: dict) -> None:
        r = self.s.exec(select(Report).where(Report.month == month)).first() or Report(month=month, json_payload="")
        r.json_payload, r.generated_at = json.dumps(payload, default=str), utcnow()
        self.s.add(r)
        self.s.commit()

    # voice log
    def add_voice_log(self, transcript: str, intents: list[dict]) -> int:
        row = VoiceLog(transcript=transcript, intent_json=json.dumps(intents))
        self.s.add(row)
        self.s.commit()
        self.s.refresh(row)
        return row.id

    def get_voice_log(self, log_id: int) -> dict | None:
        row = self.s.get(VoiceLog, log_id)
        if row is None:
            return None
        return {"id": row.id, "transcript": row.transcript, "intents": json.loads(row.intent_json),
                "confirmed": row.confirmed, "result": json.loads(row.result) if row.result else None}

    def finish_voice_log(self, log_id: int, confirmed: bool, result: dict) -> None:
        row = self.s.get(VoiceLog, log_id)
        row.confirmed, row.result = confirmed, json.dumps(result, default=str)
        self.s.add(row)
        self.s.commit()

"""In-memory stand-in for engine.planner.store.SqlStore (same method names, same dict shapes)."""
from __future__ import annotations

import datetime as dt
import re
from itertools import count


class MemoryStore:
    def __init__(self, txns=None, profile=None, goals=None):
        self.profile = profile
        self.goals: list[dict] = list(goals or [])
        self.txns: list[dict] = list(txns or [])
        self.nudges: list[dict] = []
        self.recurring: list[dict] = []
        self.rules: list[tuple[str, str]] = []  # (substring, category)
        self.reports: dict[str, dict] = {}
        self.logs: dict[int, dict] = {}
        self._ids = count(1)

    def get_profile(self):
        return dict(self.profile) if self.profile else None

    def save_profile(self, d):
        self.profile = dict(d)
        return dict(d)

    def list_goals(self):
        return sorted((dict(g) for g in self.goals), key=lambda g: (g["priority"], g["id"]))

    def add_goal(self, d):
        g = {"id": next(self._ids), **d}
        self.goals.append(g)
        return dict(g)

    def update_goal(self, goal_id, patch):
        g = next((g for g in self.goals if g["id"] == goal_id), None)
        if g is None:
            return None
        g.update(patch)
        return dict(g)

    def list_transactions(self):
        return [dict(t) for t in self.txns]

    def find_transactions(self, text):
        low = text.lower().strip()
        hits = [t for t in self.txns if low and (low in (t.get("merchant") or "").lower() or low in t.get("description", "").lower())]
        return [dict(t) for t in sorted(hits, key=lambda t: (t["date"], t["id"]), reverse=True)]

    def add_transaction(self, d):
        t = {"id": next(self._ids), "merchant": None, **d, "category": d.get("category") or "Uncategorized"}
        self.txns.append(t)
        return dict(t)

    def rule_category(self, description):
        return next((c for p, c in self.rules if re.search(re.escape(p), description, re.I)), None)

    def list_recurring(self):
        return [dict(r) for r in self.recurring]

    def list_nudges(self, include_dismissed=False):
        return [dict(n) for n in reversed(self.nudges) if include_dismissed or not n["dismissed"]]

    def add_nudge(self, d):
        n = {"id": next(self._ids), "created_at": dt.datetime.now(dt.timezone.utc).replace(tzinfo=None), "dismissed": False, **d}
        self.nudges.append(n)
        return dict(n)

    def update_nudge(self, nudge_id, fields):
        n = next((n for n in self.nudges if n["id"] == nudge_id), None)
        if n is None:
            return None
        n.update(fields)
        return dict(n)

    def save_report(self, month, payload):
        self.reports[month] = payload

    def add_voice_log(self, transcript, intents):
        i = next(self._ids)
        self.logs[i] = {"id": i, "transcript": transcript, "intents": intents, "confirmed": False, "result": None}
        return i

    def get_voice_log(self, log_id):
        return dict(self.logs[log_id]) if log_id in self.logs else None

    def finish_voice_log(self, log_id, confirmed, result):
        self.logs[log_id].update(confirmed=confirmed, result=result)

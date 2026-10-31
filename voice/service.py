"""Voice/text command flow (Person B): parse -> confirmation cards -> execute only after the user confirms.

Nothing is written by `handle_command`; `confirm` runs the intents stored server-side for that log id, so the
browser cannot change what gets executed.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date
from typing import Callable

from coach.explain import status_text, whatif_text
from coach.guardrails import guard
from engine.nudges.service import sync_nudges
from engine.planner.service import add_goal, merge_profile, overview, run_what_if
from voice.intent import confirmation, parse_command

WRITES = {"LOG_EXPENSE", "CORRECT_CATEGORY", "SET_PROFILE", "SET_GOAL"}
PatchTxn = Callable[[int, str], dict]


def patch_transaction_http(txn_id: int, category: str, opener=urllib.request.urlopen) -> dict:
    """Call Person A's PATCH /transactions/{id} per the contract. Stubbed result if their endpoint is not up yet."""
    base = os.getenv("API_BASE_URL", "http://localhost:8000")
    req = urllib.request.Request(f"{base}/transactions/{txn_id}", data=json.dumps({"category": category}).encode(),
                                 method="PATCH", headers={"Content-Type": "application/json"})
    try:
        with opener(req, timeout=10) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (404, 405):
            return {"stub": True, "message": "Transactions endpoint is not available yet; nothing was changed."}
        raise
    except urllib.error.URLError:
        return {"stub": True, "message": "Could not reach the transactions endpoint; nothing was changed."}


def _read_only(store, intent: dict, today: date) -> dict:
    """WHAT_IF / ASK_STATUS: compute the answer (no writes)."""
    if intent["type"] == "WHAT_IF":
        try:
            r = run_what_if(store, intent["params"], today)
        except (ValueError, KeyError) as e:
            return {"ok": False, "message": str(e)}
        return {"ok": True, "message": whatif_text(r), "data": r}
    o = overview(store, today)
    return {"ok": True, "message": status_text(o, sync_nudges(store, today)), "data": {"surplus": o["surplus"]}}


def _write(store, intent: dict, patch_txn: PatchTxn, today: date, transcript: str) -> dict:
    p = intent["params"]
    kind = intent["type"]
    if kind == "SET_PROFILE":
        merge_profile(store, p)
        return {"ok": True, "message": "Profile updated."}
    if kind == "SET_GOAL":
        td = date.fromisoformat(p["target_date"]) if p.get("target_date") else None
        g = add_goal(store, {"name": p["name"], "target_amount": p["target_amount"], "target_date": td})
        return {"ok": True, "message": f"Goal '{g['name']}' added.", "goal_id": g["id"]}
    if kind == "LOG_EXPENSE":
        desc = p["description"]
        given = p.get("category")
        cat = given or store.rule_category(desc)
        t = store.add_transaction({
            "date": date.fromisoformat(p["date"]) if p.get("date") else today, "amount": p["amount"], "direction": "debit",
            "description": desc, "category": cat, "category_source": "user" if given else ("rule" if cat else None),
            "source": "voice", "raw_text": transcript})
        return {"ok": True, "message": f"Logged ₹{t['amount']:,} on {desc}.", "transaction_id": t["id"]}
    # CORRECT_CATEGORY
    hits = store.find_transactions(p["merchant"])
    if not hits:
        return {"ok": False, "message": f"No transaction matching '{p['merchant']}' was found."}
    cat = p["category"].strip().title()
    res = patch_txn(hits[0]["id"], cat)
    if res.get("stub"):
        return {"ok": False, "message": res["message"]}
    return {"ok": True, "message": f"Recategorised '{p['merchant']}' as {cat}.", "transaction_id": hits[0]["id"], "result": res}


def handle_command(store, text: str, today: date, llm=None, classifier=None) -> dict:
    """Text (typed or transcribed) -> confirmation cards. Read-only intents already carry their answer."""
    text = text.strip()
    blocked = guard(text, classifier=classifier)
    if blocked:
        return {"log_id": None, "transcript": text, "blocked": True, "reply": blocked, "intents": []}
    intents = parse_command(text, today, llm=llm)
    cards = []
    for i, intent in enumerate(intents):
        writes = intent["type"] in WRITES
        card = {"index": i, "type": intent["type"], "params": intent["params"],
                "summary": confirmation(intent), "writes": writes}
        if not writes and intent["type"] != "UNKNOWN":
            card["answer"] = _read_only(store, intent, today)
        cards.append(card)
    return {"log_id": store.add_voice_log(text, intents), "transcript": text, "blocked": False, "reply": None, "intents": cards}


def confirm(store, log_id: int, accept: bool, today: date, patch_txn: PatchTxn = patch_transaction_http) -> dict | None:
    """Run the stored write-intents if accepted. None if the log id is unknown; ValueError if already resolved."""
    log = store.get_voice_log(log_id)
    if log is None:
        return None
    if log["result"] is not None:
        raise ValueError("this command was already confirmed or cancelled")
    if not accept:
        store.finish_voice_log(log_id, False, {"cancelled": True})
        return {"confirmed": False, "results": []}
    results = []
    for i in log["intents"]:
        if i["type"] in WRITES:
            try:
                results.append({"type": i["type"], **_write(store, i, patch_txn, today, log["transcript"])})
            except (KeyError, ValueError, TypeError) as e:
                results.append({"type": i["type"], "ok": False, "message": f"Could not apply this: {e}"})
    store.finish_voice_log(log_id, True, {"results": results})
    return {"confirmed": True, "results": results}

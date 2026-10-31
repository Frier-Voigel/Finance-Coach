"""Voice/text command -> intents (Person B). Regex first, optional LLM fallback for what regex misses.

Returns a list of {"type", "params"}; the API shows them as a confirmation card and writes nothing itself.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Callable

_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m} | {
    m.lower(): i for i, m in enumerate(calendar.month_abbr) if m}
_UNIT = {"crore": 10**7, "cr": 10**7, "lakh": 10**5, "lakhs": 10**5, "lac": 10**5, "k": 1000, "thousand": 1000}
_AMT = r"(?:rs\.?|₹|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(crore|cr|lakhs?|lac|k|thousand)?\b"
_FIXED = r"rent|emi|insurance|internet|electricity|loan"
_CORRECT = re.compile(
    r"\b(?:mark|set|change|categori[sz]e|recategori[sz]e|move|put|tag|label|classify)\s+(?!\d|rs\b|₹)"
    r"(?:the\s+|my\s+|all\s+)*(?:category\s+(?:of|for)\s+)?(.+?)(?:\s+(?:category|transactions?|payments?|charges?))?\s+"
    r"(?:as|to|into|under)\s+(?:the\s+)?(?:category\s+)?(.+)", re.I)
_SHOULD_BE = re.compile(r"^(?:the\s+|my\s+)?(.+?)\s+should be\s+(?:a\s+|an\s+|under\s+)?(.+?)\.?$", re.I)


def parse_amount(text: str) -> int | None:
    m = re.search(_AMT, text, re.I)
    if not m:
        return None
    return round(float(m.group(1).replace(",", "")) * _UNIT.get((m.group(2) or "").lower(), 1))


def parse_date(text: str, today: date) -> date | None:
    """'by next June', 'by March 2027', 'in 8 months' -> last day of that month."""
    low = text.lower()
    m = re.search(r"\bin (\d+) (month|year)s?\b", low)
    if m:
        n = int(m.group(1)) * (12 if m.group(2) == "year" else 1)
        y, mo = divmod(today.month - 1 + n, 12)
        return date(today.year + y, mo + 1, calendar.monthrange(today.year + y, mo + 1)[1])
    m = re.search(r"\bby\s+(?:next\s+)?([a-z]+)(?:\s+(\d{4}))?", low)
    if not m or m.group(1) not in _MONTHS:
        return None
    mo = _MONTHS[m.group(1)]
    year = int(m.group(2)) if m.group(2) else today.year + (mo <= today.month)  # next occurrence
    return date(year, mo, calendar.monthrange(year, mo)[1])


def _intent(type_: str, **params) -> dict:
    return {"type": type_, "params": params}


def _clause(c: str, today: date) -> dict | None:
    low = c.lower().strip()
    if re.match(r"(what if|what happens if)\b", low):
        m = re.search(r"\b(cut|reduce|lower|decrease|increase|raise)\b\s+(?:my\s+)?(.+?)(?:\s+spend(?:ing)?)?\s+by\s+(\d+(?:\.\d+)?)\s*%", low)
        if m:
            sign = -1 if m.group(1) in ("cut", "reduce", "lower", "decrease") else 1
            return _intent("WHAT_IF", kind="category_pct", category=m.group(2), pct=sign * float(m.group(3)))
        m = re.search(rf"\b(?:my\s+)?({_FIXED})\b.*?\b(goes up|rises|increases|goes down|drops|falls)\b.*?{_AMT}", low)
        if m:
            amt = parse_amount(low[m.start(2):]) or 0
            return _intent("WHAT_IF", kind="fixed_abs", name=m.group(1), delta=amt if m.group(2) in ("goes up", "rises", "increases") else -amt)
        m = re.search(r"\bincome\b.*?\b(goes up|rises|increases|goes down|drops|falls)\b", low)
        if m:
            amt = parse_amount(low[m.end():]) or 0
            return _intent("WHAT_IF", kind="income_abs", delta=amt if m.group(1) in ("goes up", "rises", "increases") else -amt)
        m = re.search(r"\bspend\s+" + _AMT + r"\s+(less|more)\s+on\s+(.+)", low)
        if m:
            amt = parse_amount(low[low.index("spend") + 5:]) or 0
            return _intent("WHAT_IF", kind="category_abs", category=m.group(4).strip(), delta=-amt if m.group(3) == "less" else amt)
        return None
    m = _CORRECT.search(c) or _SHOULD_BE.search(c.strip()) or \
        re.search(r"(?:that\s+)?(.+?)\s+(?:one|transaction|payment)\s+is\s+(.+?)(?:,|\s+not\b|$)", c, re.I)
    if m:
        cat = re.sub(r"\s+category$", "", m.group(2).strip().rstrip("."), flags=re.I)
        return _intent("CORRECT_CATEGORY", merchant=m.group(1).strip(), category=cat)
    m = re.search(rf"\b(?:i earn|i make|my (?:monthly )?(?:income|salary) is)\s*{_AMT}", low)
    if m:
        return _intent("SET_PROFILE", monthly_income=parse_amount(low[m.start(): ]))
    m = re.search(rf"\b(?:my\s+)?({_FIXED})\b\s+(?:is|=)\s*{_AMT}", low)
    if m:
        return _intent("SET_PROFILE", fixed_costs={m.group(1): parse_amount(low[m.end(1):])})
    if re.search(r"\b(want|need|save|goal|target)\b", low) and (amt := parse_amount(low)):
        am = re.search(_AMT, low, re.I)
        name = re.split(r"\bby\b|\bin \d", low[am.end():])[0]
        name = re.sub(r"^(?:\s*(?:for|an?|the|as|in|to save)\b)+", "", name).strip() or "goal"
        d = parse_date(low, today)
        return _intent("SET_GOAL", name=name, target_amount=amt, target_date=d.isoformat() if d else None)
    m = re.search(r"\b(?:spent|paid|bought)\s+" + _AMT + r"\s+(?:on|for|at)\s+(.+)", low)
    if m:
        when = today - timedelta(days=1) if "yesterday" in low else today
        what = re.sub(r"\s+yesterday$", "", m.group(3)).strip()
        return _intent("LOG_EXPENSE", amount=parse_amount(low[low.index(m.group(1)):]), description=what, date=when.isoformat())
    if re.search(r"\bhow (am i|are we) doing\b|\bstatus\b|\bhow'?s my month\b|\bsummary\b", low):
        return _intent("ASK_STATUS")
    return None


def parse_command(text: str, today: date, llm: Callable[[str], list[dict]] | None = None) -> list[dict]:
    """Split on commas (not inside 1,50,000), periods and 'and', parse each clause; fall back to llm."""
    out = [i for c in re.split(r",(?!\d)|\.\s+|\s+and\s+(?=i |my |what )", text) if c.strip() and (i := _clause(c, today))]
    if out:
        return out
    return (llm(text) if llm else []) or [_intent("UNKNOWN", text=text)]


def confirmation(intent: dict) -> str:
    """One-line text for the confirmation card."""
    p = intent["params"]
    return {
        "WHAT_IF": f"Run what-if: {p}",
        "CORRECT_CATEGORY": f"Recategorise '{p.get('merchant')}' as '{p.get('category')}' and remember the rule",
        "SET_PROFILE": f"Update profile: {p}",
        "SET_GOAL": f"Add goal '{p.get('name')}': ₹{p.get('target_amount', 0):,} by {p.get('target_date') or 'no date'}",
        "LOG_EXPENSE": f"Log expense ₹{p.get('amount', 0):,} on '{p.get('description')}' ({p.get('date')})",
        "ASK_STATUS": "Show how you're doing this month",
    }.get(intent["type"], "Sorry, I didn't catch that. Try typing it.")

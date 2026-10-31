"""Plain-language wrappers around planner output (Person B).

The text is built from numbers computed in Python. An LLM may only re-phrase it: if its answer contains a number
that is not in the facts (or breaks the securities rule), the deterministic text is used instead.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Callable

from coach.guardrails import output_violates
from engine.reports.report import FOOTER

LLM = Callable[[str], str | None]


def _money(n: int) -> str:
    return f"₹{n:,}"


def _when(d: date | None) -> str:
    return d.strftime("%b %Y") if d else "not reachable at the current surplus"


def whatif_text(r: dict) -> str:
    """Before/after sentence for a what_if() result."""
    lines = [f"Monthly surplus would go from {_money(r['surplus_before'])} to {_money(r['surplus_after'])} "
             f"({r['surplus_delta']:+,})."]
    for b, a in zip(r["before"], r["after"], strict=True):
        saved = a.get("months_saved")
        tail = f" ({abs(saved)} month{'s' if abs(saved) != 1 else ''} {'earlier' if saved > 0 else 'later'})" if saved else ""
        lines.append(f"{a['name']}: {_when(b['projected_date'])} -> {_when(a['projected_date'])}{tail}.")
    return " ".join(lines)


def status_text(o: dict, nudges: list[dict]) -> str:
    """Short 'how am I doing' summary from planner.service.overview() and open nudges."""
    p = o["profile"]
    lines = [f"Income {_money(p['monthly_income'])}, fixed costs {_money(sum(p['fixed_costs'].values()))}, "
             f"usual variable spend {_money(sum(o['variable'].values()))}: surplus {_money(o['surplus'])} a month."]
    for g in o["projections"]:
        lines.append(f"{g['name']}: {_when(g['projected_date'])}" + (" (on track)." if g["on_track"] else "."))
    lines += [n["message"] for n in nudges[:3]]
    return " ".join(lines)


def _nums(s: str) -> set[str]:
    return {m.replace(",", "") for m in re.findall(r"\d[\d,]*", s)}


def phrase(facts: str, question: str = "", llm: LLM | None = None) -> str:
    """Let the LLM re-phrase `facts` in a friendlier voice, but only keep the result if no new numbers appear."""
    if llm:
        out = llm(
            "Rewrite these facts for a friendly money coach in at most 4 sentences. Do not change, add or round any "
            "number. Never name or recommend any stock, fund, ETF or crypto.\n"
            f"Question: {question}\nFacts: {facts}"
        )
        if out and _nums(out) <= _nums(facts) | _nums(question) and not output_violates(out):
            return out.strip()
    return facts


def with_footer(text: str) -> str:
    return f"{text}\n\n{FOOTER}"

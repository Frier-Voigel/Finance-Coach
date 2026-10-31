"""LLM fallback for the intent router (Person B). Used only when the regex parser finds nothing.

The model extracts fields into a strict JSON shape; this module validates it, so a bad answer becomes "no intents".
It never computes numbers: amounts are taken as the user said them.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Callable

SCHEMA = {
    "LOG_EXPENSE": {"amount", "description", "category", "date"},
    "CORRECT_CATEGORY": {"merchant", "category"},
    "SET_PROFILE": {"monthly_income", "fixed_costs"},
    "SET_GOAL": {"name", "target_amount", "target_date"},
    "WHAT_IF": {"kind", "category", "name", "pct", "delta"},
    "ASK_STATUS": set(),
}
_PROMPT = (
    "Turn the user's message into a JSON array of intents. Reply with JSON only.\n"
    "Allowed intents and params (whole rupees as integers, dates as YYYY-MM-DD):\n"
    + "\n".join(f"- {k}: {sorted(v)}" for k, v in SCHEMA.items())
    + '\nWHAT_IF kinds: category_pct {category, pct (negative = cut)}, category_abs {category, delta}, '
    "fixed_abs {name, delta}, income_abs {delta}.\n"
    'Shape: [{"type": "...", "params": {...}}]. If nothing matches reply [].\nMessage: '
)


def validate(raw: str | None) -> list[dict]:
    """Parse and filter the model output; anything off-schema is dropped."""
    if not raw:
        return []
    try:
        data = json.loads(re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip())
    except ValueError:
        return []
    out = []
    for i in data if isinstance(data, list) else []:
        if isinstance(i, dict) and i.get("type") in SCHEMA and isinstance(i.get("params", {}), dict):
            params = {k: v for k, v in i.get("params", {}).items() if k in SCHEMA[i["type"]] and v is not None}
            out.append({"type": i["type"], "params": params})
    return out


def make_llm_parser(generate: Callable[[str], str | None]) -> Callable[[str], list[dict]]:
    """Cached text -> intents function for parse_command(llm=...)."""

    @lru_cache(maxsize=256)
    def parse(text: str) -> tuple:
        return tuple(validate(generate(_PROMPT + text)))

    return lambda text: [dict(i) for i in parse(text)]

"""LLM fallback for text the rules cannot parse (SMS, messy PDFs).

The LLM only extracts text fields as JSON. Dates and amounts are re-parsed by
deterministic code, and anything that fails validation is dropped.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Callable

from ingest.models import ParsedTxn
from ingest.normalizer import clean_merchant, parse_amount, parse_date

LLM = Callable[[str], str]
_CACHE: dict[str, list[dict]] = {}

PROMPT = (
    "Extract bank transactions from the text below. Reply with ONLY a JSON array of objects "
    'with keys "date" (as written), "description", "amount" (as written, no math) and '
    '"direction" ("debit" or "credit"). Return [] if there are none. Do not invent data.\n\n'
)


def extract_with_llm(text: str, source: str, llm: LLM, default_year: int | None = None,
                     account: str = "") -> list[ParsedTxn]:
    """Ask the LLM to pull transactions from `text`; cache by content hash."""
    key = hashlib.sha256(text.encode()).hexdigest()
    if key not in _CACHE:
        _CACHE[key] = _decode_json(llm(PROMPT + text))
    out: list[ParsedTxn] = []
    for item in _CACHE[key]:
        try:
            direction = str(item["direction"]).lower()
            if direction not in ("debit", "credit"):
                continue
            desc = str(item["description"]).strip()
            out.append(ParsedTxn(
                parse_date(str(item["date"]), default_year), abs(parse_amount(str(item["amount"]))),
                direction, desc, clean_merchant(desc), source, text.strip(), account))
        except (KeyError, ValueError, TypeError):
            continue
    return out


def _decode_json(reply: str) -> list[dict]:
    cleaned = re.sub(r"```(?:json)?", "", reply).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return []
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []

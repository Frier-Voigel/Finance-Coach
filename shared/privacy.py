"""Redact identifiers before any text leaves the server for an LLM. Applied centrally in the Gemini wrappers."""
from __future__ import annotations

import re

_RULES = [
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*"), "[id]"),  # emails and UPI handles (name@okaxis)
    (re.compile(r"(?<!\d)(?:\+?91[ -]?)?[6-9]\d{4}[ -]?\d{5}(?!\d)"), "[phone]"),  # Indian mobile numbers
    (re.compile(r"(?<!\d)\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{2,4}(?!\d)"), "[acct]"),  # grouped card numbers
    (re.compile(r"\b\d{4}X{2,}\d{2,4}\b|\bX{2,}\d{2,6}\b", re.I), "[acct]"),  # 4567XX1234, XX1234
    (re.compile(r"(?<!\d)\d{9,}(?!\d)"), "[acct]"),  # account numbers, long references
]


def mask(text: str) -> str:
    """Replace account/card/phone numbers, emails and UPI handles with placeholders. Amounts and dates are kept."""
    for pattern, repl in _RULES:
        text = pattern.sub(repl, text)
    return text

"""Helpers to clean merchant names, parse dates/amounts and dedupe transactions."""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from dateutil import parser as _dparser

from ingest.models import ParsedTxn

_DATE_FORMATS = (
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d %b %Y",
    "%d-%b-%y", "%d/%m/%y", "%d-%m-%y", "%d %b %y", "%d %B %Y", "%Y/%m/%d",
)
_UPI_STOP = {"PAYMENT", "PAID", "UPI", "DR", "CR", "PAY", "MANDATE", "COLLECT"}
_IFSC = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_CHANNELS = re.compile(
    r"\b(UPI|POS|ECOM|NEFT|IMPS|RTGS|ACH|ATM|ECS|NACH|DEBIT CARD|CARD|PURCHASE|TXN|TRF)\b"
)


def parse_date(text: str, default_year: int | None = None) -> date:
    """Parse many bank date formats (day-first) to a `date`. Raises ValueError."""
    s = (text or "").strip()
    if not s:
        raise ValueError("empty date")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    if not re.search(r"\d", s):
        raise ValueError(f"unparseable date: {text!r}")
    default = datetime(default_year or date.today().year, 1, 1)
    try:
        return _dparser.parse(s, dayfirst=True, default=default).date()
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"unparseable date: {text!r}") from exc


def parse_amount(text: str) -> Decimal:
    """Parse '1,234.50', 'Rs. 450', '(200.00)', '300 Dr' to a signed Decimal.

    Negative for parentheses, a leading minus or a 'Dr' suffix; 'Cr' is positive.
    """
    s = (text or "").strip()
    if not s:
        raise ValueError("empty amount")
    negative = s.startswith("(") and s.endswith(")") or s.startswith("-")
    if re.search(r"\bdr\.?$", s, re.I):
        negative = True
    m = re.search(r"\d[\d,]*(?:\.\d+)?", s)
    if not m:
        raise ValueError(f"unparseable amount: {text!r}")
    try:
        value = Decimal(m.group(0).replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"unparseable amount: {text!r}") from exc
    return -value if negative else value


def clean_merchant(description: str) -> str:
    """Strip UPI ids, reference numbers and channel words; return an uppercase merchant."""
    raw = (description or "").strip()
    if raw.upper().startswith("UPI"):
        for part in re.split(r"[/-]", raw)[1:]:
            p = part.strip()
            if (p and not p.isdigit() and "@" not in p
                    and p.upper() not in _UPI_STOP and not _IFSC.match(p.upper())):
                return re.sub(r"\s+", " ", p.upper())
    s = raw.upper()
    s = re.sub(r"\S+@\S+", " ", s)
    s = _CHANNELS.sub(" ", s)
    s = re.sub(r"\b(?=[\dX*]*\d)[\dX*]{4,}\b|\b[A-Z]{4}0[A-Z0-9]{6}\b", " ", s)
    s = re.sub(r"[^A-Z0-9 &.]", " ", s)
    return re.sub(r"\s+", " ", s).strip(" .") or raw.upper()


def txn_key(t: ParsedTxn) -> tuple:
    """Base identity of a transaction used for dedupe."""
    return (t.date.isoformat(), str(t.amount), t.direction, t.merchant, t.account)


def dedupe(new: list[ParsedTxn], existing_keys: set[tuple] | None = None) -> list[ParsedTxn]:
    """Drop transactions already imported.

    Keys carry an occurrence counter so two genuine identical purchases on one
    day in the same file both survive, while re-uploading the file adds nothing.
    """
    existing = existing_keys or set()
    seen: dict[tuple, int] = {}
    out: list[ParsedTxn] = []
    for t in new:
        base = txn_key(t)
        seen[base] = seen.get(base, 0) + 1
        if (*base, seen[base]) not in existing:
            out.append(t)
    return out


def keys_for(txns: list[ParsedTxn]) -> set[tuple]:
    """Counter-aware keys for already-stored transactions (pass to `dedupe`)."""
    seen: dict[tuple, int] = {}
    keys: set[tuple] = set()
    for t in txns:
        base = txn_key(t)
        seen[base] = seen.get(base, 0) + 1
        keys.add((*base, seen[base]))
    return keys

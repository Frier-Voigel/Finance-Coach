"""Regex SMS parser for Indian bank transaction alerts. Unmatched text goes to the LLM fallback."""
from __future__ import annotations

import re
from datetime import date

from ingest.models import ParsedTxn
from ingest.normalizer import clean_merchant, parse_amount, parse_date

_AMOUNT = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)", re.I)
_DEBIT = re.compile(r"\b(debited|spent|paid|withdrawn|sent|purchase)\b", re.I)
_CREDIT = re.compile(r"\b(credited|received|deposited|refund(?:ed)?)\b", re.I)
_DATE = re.compile(
    r"\bon\s+(\d{1,2}[-/ ][A-Za-z]{3,9}(?:[-/ ]\d{2,4})?|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", re.I)
_ACCOUNT = re.compile(r"(?:A/c|a/c|account|card)\s*(?:no\.?)?\s*([X*]*\d{3,4})", re.I)
_MERCHANT_DEBIT = re.compile(
    r"\b(?:at|to|towards)\s+([A-Za-z0-9 &._*@-]+?)(?=\s+on\s|\s+Ref|\s+UPI|\.\s|\.$|$)", re.I)
_MERCHANT_CREDIT = re.compile(
    r"\b(?:by|from)\s+([A-Za-z0-9 &._*@-]+?)(?=\s+on\s|\s+Ref|\s+UPI|\.\s|\.$|$)", re.I)


def parse_sms(text: str, default_year: int | None = None) -> ParsedTxn | None:
    """Parse one SMS. Returns None if it is not a recognizable transaction alert."""
    amt = _AMOUNT.search(text)
    if not amt:
        return None
    is_debit, is_credit = _DEBIT.search(text), _CREDIT.search(text)
    if bool(is_debit) == bool(is_credit):
        return None
    direction = "debit" if is_debit else "credit"
    m_date = _DATE.search(text)
    if not m_date:
        return None
    try:
        d = parse_date(m_date.group(1), default_year or date.today().year)
    except ValueError:
        return None
    m_merch = (_MERCHANT_DEBIT if direction == "debit" else _MERCHANT_CREDIT).search(text)
    # skip the "debited from A/c" style capture: merchant must not be the account phrase
    raw_merchant = m_merch.group(1).strip() if m_merch else ""
    if re.match(r"(?i)a/c|account|card", raw_merchant):
        raw_merchant = ""
    acct = _ACCOUNT.search(text)
    return ParsedTxn(
        d, abs(parse_amount(amt.group(1))), direction, raw_merchant or text.strip(),
        clean_merchant(raw_merchant) if raw_merchant else "UNKNOWN", "sms", text.strip(),
        acct.group(1) if acct else "",
    )


def parse_sms_batch(blob: str, default_year: int | None = None) -> tuple[list[ParsedTxn], list[str]]:
    """Split pasted text into messages (one per non-empty line); return (parsed, unmatched)."""
    parsed: list[ParsedTxn] = []
    unmatched: list[str] = []
    for line in (l.strip() for l in blob.splitlines()):
        if not line:
            continue
        t = parse_sms(line, default_year)
        (parsed.append(t) if t else unmatched.append(line))
    return parsed, unmatched

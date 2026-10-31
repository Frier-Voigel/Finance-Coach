"""CSV statement parser with column auto-mapping for different bank layouts."""
from __future__ import annotations

import csv
import io
import re
from decimal import Decimal

from ingest.models import ParsedTxn
from ingest.normalizer import clean_merchant, parse_amount, parse_date

_SYNONYMS = {
    "date": {"date", "txn date", "transaction date", "value date", "posting date", "tran date"},
    "description": {"description", "narration", "particulars", "details", "remarks",
                    "transaction remarks", "transaction details"},
    "debit": {"debit", "withdrawal", "withdrawals", "withdrawal amt", "debit amount", "dr", "paid out"},
    "credit": {"credit", "deposit", "deposits", "deposit amt", "credit amount", "cr", "paid in"},
    "amount": {"amount", "txn amount", "transaction amount"},
    "balance": {"balance", "closing balance", "running balance"},
    "type": {"type", "dr/cr", "cr/dr", "txn type", "transaction type"},
}


def _norm(h: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z/ ]", "", h.lower())).strip()


def _decode(content: str | bytes) -> str:
    if isinstance(content, str):
        return content
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def _map_columns(row: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, cell in enumerate(row):
        n = _norm(cell)
        for field, names in _SYNONYMS.items():
            if n in names and field not in mapping:
                mapping[field] = idx
    return mapping


def _delimiter(text: str) -> str:
    head = "\n".join(text.splitlines()[:15])
    return max(",;\t|", key=head.count)


def parse_csv(content: str | bytes, account: str = "") -> list[ParsedTxn]:
    """Parse a bank CSV into transactions. Skips preamble/footer rows.

    Raises ValueError if no header row with a date and description is found.
    """
    text = _decode(content)
    rows = list(csv.reader(io.StringIO(text), delimiter=_delimiter(text)))
    return parse_rows(rows, "csv", account)


def parse_rows(rows: list[list[str]], source: str, account: str = "") -> list[ParsedTxn]:
    """Map header-bearing table rows (from CSV or a PDF table) to transactions."""
    header_idx, cols = None, {}
    for i, row in enumerate(rows):
        m = _map_columns(row)
        if "date" in m and "description" in m and ({"debit", "credit", "amount"} & m.keys()):
            header_idx, cols = i, m
            break
    if header_idx is None:
        raise ValueError("could not find a header row with date, description and amount columns")

    out: list[ParsedTxn] = []
    for row in rows[header_idx + 1:]:
        def cell(field: str) -> str:
            i = cols.get(field)
            return row[i].strip() if i is not None and i < len(row) else ""

        try:
            d = parse_date(cell("date"))
        except ValueError:
            continue  # opening balance, totals, blank lines
        parsed = _direction_and_amount(cell, cols)
        if parsed is None:
            continue
        direction, amount = parsed
        desc = cell("description")
        balance = None
        if cell("balance"):
            try:
                balance = abs(parse_amount(cell("balance")))
            except ValueError:
                pass
        out.append(ParsedTxn(d, amount, direction, desc, clean_merchant(desc), source,
                             ",".join(row), account, balance))
    return out


def _direction_and_amount(cell, cols) -> tuple[str, Decimal] | None:
    """Work out (direction, positive amount) from debit/credit, signed or typed columns."""
    if "debit" in cols or "credit" in cols:
        for field, direction in (("debit", "debit"), ("credit", "credit")):
            if cell(field):
                try:
                    value = abs(parse_amount(cell(field)))
                except ValueError:
                    continue
                if value > 0:
                    return direction, value
        if "amount" not in cols:
            return None
    if not cell("amount"):
        return None
    value = parse_amount(cell("amount"))
    kind = cell("type").upper()
    if kind.startswith(("DR", "D")):
        return "debit", abs(value)
    if kind.startswith(("CR", "C")):
        return "credit", abs(value)
    if value == 0:
        return None
    return ("debit", -value) if value < 0 else ("credit", value)

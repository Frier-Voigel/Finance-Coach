"""Parser output shared by all ingest parsers (maps onto the `transactions` table)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class ParsedTxn:
    """One normalized transaction. `amount` is always positive; see `direction`."""

    date: date
    amount: Decimal
    direction: str  # "debit" | "credit"
    description: str
    merchant: str
    source: str  # "csv" | "pdf" | "sms"
    raw_text: str = ""
    account: str = ""
    balance: Decimal | None = None

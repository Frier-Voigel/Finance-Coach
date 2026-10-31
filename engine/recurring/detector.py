"""Recurring subscription / payment detection."""
from __future__ import annotations

import hashlib
import statistics
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from shared.schema import Transaction

# Cadence windows (days): (min, max, label)
_CADENCES = [
    (2, 10, "weekly"),
    (25, 35, "monthly"),
    (360, 366, "yearly"),
]


def cadence_label(median_days: float) -> Optional[str]:
    """Map a median inter-transaction gap to a cadence string.

    Returns ``"weekly"``, ``"monthly"``, ``"yearly"``, or ``None``.
    """
    for low, high, label in _CADENCES:
        if low <= median_days <= high:
            return label
    return None


def _modal_amount(amounts: list[Decimal]) -> Decimal:
    """Return the most common amount (or median for floats)."""
    freq: dict[Decimal, int] = {}
    for a in amounts:
        freq[a] = freq.get(a, 0) + 1
    return max(freq, key=lambda k: freq[k])


def _price_steps(amounts: list[Decimal]) -> int:
    """Count jumps of more than 5% between consecutive payments."""
    return sum(1 for a, b in zip(amounts, amounts[1:]) if a == 0 or abs(float(b - a)) / float(a) > 0.05)


def detect_recurring(txns: list[Transaction]) -> list[dict]:
    """Detect recurring merchants from a transaction list.

    Algorithm
    ---------
    1. Group by merchant.
    2. Skip groups with fewer than 3 transactions.
    3. Sort by date; compute gaps between consecutive dates.
    4. Classify cadence via ``cadence_label`` (median gap ± tolerance).
    5. Only debits count. Allow at most one >5% price change in the history;
       flag ``"changed"`` if that change happened in the last 3 payments.

    Returns
    -------
    list[dict]
        Each dict has: ``merchant``, ``cadence``, ``amount``, ``last_seen``,
        ``next_expected``, ``status``.
    """
    # Group by merchant
    groups: dict[str, list[Transaction]] = {}
    for t in txns:
        if t.direction != "debit":  # salary, refunds and other money in are not subscriptions
            continue
        groups.setdefault(t.merchant, []).append(t)

    results: list[dict] = []
    for merchant, group in groups.items():
        if len(group) < 3:
            continue

        sorted_group = sorted(group, key=lambda t: t.date)
        dates: list[date] = [t.date for t in sorted_group]
        amounts: list[Decimal] = [t.amount for t in sorted_group]

        # Compute inter-date gaps
        gaps: list[float] = [
            (dates[i] - dates[i - 1]).days for i in range(1, len(dates))
        ]
        median_gap = statistics.median(gaps)
        label = cadence_label(median_gap)
        if label is None:
            continue

        # Amount regularity: allow one price change (a hike that has stuck); several means irregular spending.
        if _price_steps(amounts) > 1:
            continue
        modal = _modal_amount(amounts)

        last_seen = dates[-1]
        cadence_days = {"weekly": 7, "monthly": 30, "yearly": 365}[label]
        next_expected = last_seen + timedelta(days=cadence_days)

        # Determine status
        changed = _price_steps(amounts[-4:]) > 0  # price moved within the last 3 payments
        status = "changed" if changed else "active"

        results.append(
            {
                "merchant": merchant,
                "cadence": label,
                "amount": modal,
                "last_seen": last_seen,
                "next_expected": next_expected,
                "status": status,
                "merchant_hash": hashlib.md5(merchant.encode()).hexdigest(),
            }
        )

    return results

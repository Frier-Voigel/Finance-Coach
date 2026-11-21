"""Turn a blocked 'which stock?' question into something useful: a what-if of investing part of the surplus."""
from __future__ import annotations

INVEST_NAME = "Monthly investing"


def invest_offer(surplus: int) -> dict | None:
    """Suggest half the monthly surplus (rounded down to ₹500) as an amount to model. None if there is no room."""
    amount = surplus // 2 // 500 * 500
    if amount < 500:
        return None
    return {"kind": "fixed_abs", "name": INVEST_NAME, "amount": amount, "surplus": surplus}

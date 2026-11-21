"""Subscription review logic (pure functions, no DB, no LLM).

Bank data shows what you PAY, never whether you USE a service, so this module only flags things worth asking
about and carries the user's own answers. It never decides that something is unused.
"""
from __future__ import annotations

from datetime import date, timedelta

DISCLAIMER = ("Bank data shows what you pay, not whether you use a service. "
              "We can't see usage, so we ask you instead of guessing.")

ANSWER_VALID_DAYS = 90  # a 'still using' answer is asked again after this long
PER_YEAR = {"weekly": 52, "monthly": 12, "yearly": 1}

# Overlap groups: lower-case substrings of the merchant name. Heuristic and deliberately small; extend freely.
GROUPS: dict[str, tuple[str, ...]] = {
    "Video streaming": ("netflix", "hotstar", "prime video", "amazon prime", "disney", "zee5", "sonyliv", "sony liv",
                        "jiocinema", "jio cinema", "apple tv", "youtube premium", "mubi"),
    "Music streaming": ("spotify", "wynk", "gaana", "jiosaavn", "saavn", "apple music", "youtube music"),
    "Cloud storage": ("google one", "icloud", "dropbox", "onedrive"),
    "Fitness": ("cult", "gym", "fitpass", "fitness"),
    "Food delivery pass": ("swiggy one", "zomato gold"),
}


def group_of(merchant: str) -> str | None:
    low = merchant.lower()
    return next((g for g, words in GROUPS.items() if any(w in low for w in words)), None)


def yearly_cost(amount: int, cadence: str) -> int:
    return round(amount * PER_YEAR.get(cadence, 12))


def _pct(part: int, income_monthly: int) -> float | None:
    return round(part / (income_monthly * 12) * 100, 1) if income_monthly > 0 else None


def build_review(subs: list[dict], income_monthly: int, answers: dict[str, dict], today: date) -> dict:
    """subs: {merchant, merchant_hash, cadence, status, amount} where amount is the LATEST charge, in whole rupees.
    answers: {merchant: {"answer": "using"|"not_using", "answered_on": date}}.
    """
    live = [s for s in subs if s["status"] != "cancelled"]
    by_group: dict[str, list[str]] = {}
    for s in live:
        g = group_of(s["merchant"])
        if g and s["status"] in ("active", "changed"):
            by_group.setdefault(g, []).append(s["merchant"])
    overlaps = {g: m for g, m in by_group.items() if len(m) >= 2}

    items = []
    for s in live:
        g = group_of(s["merchant"])
        mates = [m for m in overlaps.get(g, []) if m != s["merchant"]]
        a = answers.get(s["merchant"])
        fresh = bool(a) and (today - a["answered_on"]) <= timedelta(days=ANSWER_VALID_DAYS)
        yearly = yearly_cost(s["amount"], s["cadence"])
        reasons = []
        if mates:
            reasons.append(f"overlaps with {', '.join(mates)} ({g.lower()})")
        if s["status"] == "changed":
            reasons.append("price changed recently")
        pct = _pct(yearly, income_monthly)
        if pct is not None and pct >= 1:
            reasons.append(f"{pct}% of your income per year")
        items.append({
            "merchant": s["merchant"], "merchant_hash": s["merchant_hash"], "cadence": s["cadence"], "status": s["status"],
            "amount": s["amount"], "yearly_cost": yearly, "pct_of_income": pct, "group": g, "overlaps_with": mates,
            "answer": a["answer"] if fresh else None, "reasons": reasons,
            "ask": s["status"] in ("active", "changed") and not fresh,
        })
    # most worth asking about first: overlaps, then price changes, then biggest yearly cost
    items.sort(key=lambda i: (not i["overlaps_with"], i["status"] != "changed", -i["yearly_cost"]))

    total = sum(i["yearly_cost"] for i in items)
    dropped = sum(i["yearly_cost"] for i in items if i["status"] == "unused" or i["answer"] == "not_using")
    return {
        "disclaimer": DISCLAIMER,
        "total_yearly_cost": total,
        "total_pct_of_income": _pct(total, income_monthly),
        "potential_yearly_savings": dropped,
        "overlaps": [{"group": g, "merchants": m,
                      "yearly_cost": sum(i["yearly_cost"] for i in items if i["merchant"] in m),
                      "message": f"{' and '.join(m)} are both {g.lower()}. We can't see whether you use both, so it's worth asking."}
                     for g, m in overlaps.items()],
        "items": items,
    }

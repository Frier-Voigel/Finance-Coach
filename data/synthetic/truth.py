"""Labelled benchmark rows: statement-style descriptions with the category the generator knows is right."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from data.synthetic.generate import Entry, describe
from ingest.normalizer import clean_merchant

# merchant as it appears on a statement -> true category (categorizer taxonomy)
KNOWN = {  # also in the built-in merchant list
    "SWIGGY": "Food", "ZOMATO": "Food", "BIGBASKET": "Food", "CAFE COFFEE DAY": "Food", "UBER INDIA": "Transport",
    "DMART": "Shopping", "AMAZON PAY INDIA": "Shopping", "MYNTRA": "Shopping", "NETFLIX": "Subscriptions",
    "SPOTIFY": "Subscriptions", "GYMFIT": "Health", "JIO PREPAID": "Utilities", "BSES RAJDHANI": "Utilities",
    "LANDLORD RAJESH": "Rent", "ACME TECHNOLOGIES": "Salary",
}
UNSEEN = {  # real-world merchants the built-in list has never heard of
    "BLINKIT": "Food", "ZEPTO": "Food", "BARBEQUE NATION": "Food", "RELIANCE FRESH": "Food", "OLA": "Transport",
    "IRCTC": "Transport", "METRO CARD RECHARGE": "Transport", "FLIPKART": "Shopping", "BOOKMYSHOW": "Entertainment",
    "PVR CINEMAS": "Entertainment", "APOLLO PHARMACY": "Health", "PRACTO": "Health", "AIRTEL": "Utilities",
    "TATA POWER": "Utilities", "HOTSTAR": "Subscriptions", "CULT FIT": "Health",
}
CHANNELS = ("upi", "pos", "ecom")


def build_rows(seed: int = 7) -> list[tuple[str, str, str]]:
    """(merchant, description, true category) for ~170 transactions; merchant is cleaned exactly as ingest does."""
    rnd = random.Random(seed)
    rows: list[tuple[str, str, str]] = []
    for name, cat in {**KNOWN, **UNSEEN}.items():
        for _ in range(rnd.randint(3, 6) if name in UNSEEN else rnd.randint(2, 4)):
            e = Entry(date(2026, 9, 1), name, Decimal("100.00"), "debit", rnd.choice(CHANNELS))
            desc = describe(e, len(rows), rnd.choice(("dash", "slash")))
            rows.append((clean_merchant(desc), desc, cat))
    rnd.shuffle(rows)
    return rows

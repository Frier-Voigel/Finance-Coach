"""Deterministic generator of synthetic bank data (fully unified for Person A & Person B).

Supports:
- Person A: 3 CSV layouts, 1 PDF statement, SMS alerts text, `generate()`, `build_ledger()`, `Entry`.
- Person B: `build(as_of)`, `sms_text(t)`, `write_files()`, `generate_transactions()`, `generate_profile()`.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import datetime as dt
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path
import random

from dateutil.relativedelta import relativedelta

# ---------------------------------------------------------------------------
# Person B Generator: build(as_of), write_files, sms_text
# ---------------------------------------------------------------------------

SEED = 42
INCOME = 75000

VARIABLE = [
    ("Groceries", ["BigBasket", "Blinkit", "Zepto", "Reliance Fresh"], (250, 1400), 9),
    ("Dining", ["Swiggy", "Zomato", "Barbeque Nation", "Cafe Coffee Day"], (180, 900), 8),
    ("Transport", ["Uber", "Ola", "Metro Card Recharge"], (90, 450), 10),
    ("Shopping", ["Amazon", "Myntra", "Flipkart"], (400, 2800), 3),
    ("Entertainment", ["BookMyShow", "PVR Cinemas"], (250, 700), 2),
    ("Health", ["Apollo Pharmacy", "Practo"], (200, 1200), 1),
]
RENT_BEFORE, RENT_AFTER = 22000, 24000
FIXED = {"Rent": RENT_AFTER, "Utilities": 3200, "Subscriptions": 2268}
SUBSCRIPTIONS = [  # merchant, category, amount, day of month
    ("Netflix", "Subscriptions", 649, 5),
    ("Spotify", "Subscriptions", 119, 9),
    ("Cult.fit Gym", "Subscriptions", 1500, 12),
]


def _month_starts(as_of: date, back: int = 6) -> list[date]:
    first = as_of.replace(day=1)
    return [first - relativedelta(months=i) for i in range(back, -1, -1)]


def build(as_of: date = date(2026, 10, 15), seed: int = SEED) -> dict:
    """Build canonical seed dictionary compatible with test_phase0_data.py."""
    rnd = random.Random(seed)
    txns: list[dict] = []

    def add(d: date, amount: int, direction: str, desc: str, merchant: str | None, category: str, source: str = "csv") -> None:
        if d <= as_of:
            txns.append({"date": d, "amount": amount, "direction": direction, "description": desc, "merchant": merchant,
                         "category": category, "category_source": "rule", "source": source, "account": "HDFC Savings"})

    for ms in _month_starts(as_of):
        last = calendar.monthrange(ms.year, ms.month)[1]
        is_current = (ms.year, ms.month) == (as_of.year, as_of.month)
        add(ms.replace(day=1), INCOME, "credit", "SALARY ACME TECH PVT LTD", "Acme Tech", "Income")
        rent = RENT_AFTER if ms >= as_of.replace(day=1) - relativedelta(months=2) else RENT_BEFORE  # the rent increase
        add(ms.replace(day=2), rent, "debit", "NEFT-RENT-R S MEHTA", "Landlord", "Rent")
        add(ms.replace(day=7), FIXED["Utilities"] + rnd.randint(-300, 300), "debit", "BESCOM ELECTRICITY BILL", "BESCOM", "Utilities")
        for name, cat, amt, day in SUBSCRIPTIONS:
            price = amt + (150 if name == "Netflix" and (ms >= as_of.replace(day=1) - relativedelta(months=1)) else 0)
            add(ms.replace(day=min(day, last)), price, "debit", f"{name.upper()} SUBSCRIPTION", name, cat)
        for cat, merchants, (lo, hi), per_month in VARIABLE:
            n = per_month if not is_current else max(1, round(per_month * as_of.day / last))  # month to date
            if is_current and cat == "Dining":
                n += 6  # the drift the nudge should catch
            for _ in range(n):
                m = rnd.choice(merchants)
                day = rnd.randint(1, last) if not is_current else rnd.randint(1, as_of.day)
                amount = rnd.randint(lo, hi) * (2 if (is_current and cat == "Dining") else 1)
                ref = rnd.randint(100000, 999999)
                style = rnd.choice(["UPI-{m}-{ref}", "POS {m} CARD XX1234", "UPI/{ref}/{m}/PAY"])  # UPI and card-style narrations
                add(ms.replace(day=day), amount, "debit", style.format(m=m.upper(), ref=ref), m, cat)

    profile = {"monthly_income": INCOME, "fixed_costs": dict(FIXED), "emergency_fund_current": 40000, "emergency_fund_target": 200000}
    goals = [
        {"name": "Goa trip", "target_amount": 60000, "current_amount": 10000, "target_date": as_of + relativedelta(months=12), "priority": 1},
        {"name": "New laptop", "target_amount": 90000, "current_amount": 0, "target_date": as_of + relativedelta(months=18), "priority": 2},
    ]
    recurring = [
        {"merchant": "Netflix", "amount": 799, "cadence": "monthly", "last_seen": as_of.replace(day=5), "status": "changed"},
        {"merchant": "Spotify", "amount": 119, "cadence": "monthly", "last_seen": as_of.replace(day=9), "status": "active"},
        {"merchant": "Cult.fit Gym", "amount": 1500, "cadence": "monthly", "last_seen": as_of.replace(day=12), "status": "unused"},
    ]
    txns.sort(key=lambda t: t["date"])
    return {"transactions": txns, "profile": profile, "goals": goals, "recurring": recurring}


def sms_text(t: dict | Entry) -> str:
    """Bank-style SMS alert for one transaction."""
    if isinstance(t, Entry):
        when = t.day.strftime("%d-%b-%y")
        if t.direction == "credit":
            return f"Rs.{t.amount} credited to A/c XX1234 on {when} by {t.merchant}. Avl bal Rs.50000.00"
        prep = "to" if t.merchant == "LANDLORD RAJESH" else "at"
        return f"Rs.{t.amount} debited from A/c XX1234 {prep} {t.merchant} on {when}. Avl bal Rs.40000.00"
    else:
        when = t["date"].strftime("%d-%b-%y")
        merch = (t.get("merchant") or t.get("description") or "MERCHANT").upper()
        amt = t["amount"]
        if t.get("direction") == "credit":
            return f"Rs.{amt}.00 credited to A/c XX1234 on {when} by {merch}. Avl bal Rs.50000.00"
        prep = "to" if "LANDLORD" in merch else "at"
        return f"Rs.{amt}.00 debited from A/c XX1234 {prep} {merch} on {when}. Avl bal Rs.40000.00"


def write_files(data: dict, out_dir: str) -> None:
    """Two bank CSV layouts, SMS alerts and a JSON dump of profile, goals and subscriptions."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    txns = data["transactions"]
    with open(out / "bank_statement_a.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Narration", "Debit", "Credit"])
        for t in txns:
            deb, cred = (t["amount"], "") if t["direction"] == "debit" else ("", t["amount"])
            w.writerow([f"{t['date']:%d/%m/%Y}", t["description"], deb, cred])
    with open(out / "bank_statement_b.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Txn Date", "Details", "Amount", "Balance"])
        bal = 50000
        for t in txns:
            signed = t["amount"] if t["direction"] == "credit" else -t["amount"]
            bal += signed
            w.writerow([t["date"].isoformat(), t["description"], signed, bal])
    debits = [t for t in txns if t["direction"] == "debit" and t["category"] not in FIXED][-15:]
    (out / "sms_messages.txt").write_text("\n".join(sms_text(t) for t in debits) + "\n", encoding="utf-8")
    with open(out / "profile_goals.json", "w", encoding="utf-8") as f:
        json.dump({k: data[k] for k in ("profile", "goals", "recurring")}, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Person A Generator (Ledger, 3 CSVs, PDF, SMS)
# ---------------------------------------------------------------------------

MONTHS_A = [(2025, m) for m in range(4, 10)]
OPENING_BALANCE_A = Decimal("25000.00")


@dataclass(frozen=True)
class Entry:
    day: date
    merchant: str
    amount: Decimal
    direction: str  # debit | credit
    channel: str  # upi | pos | ecom | neft


def build_ledger(seed: int = 42) -> list[list[Entry]]:
    """Return one list of entries per month, in date order."""
    rng = random.Random(seed)
    months: list[list[Entry]] = []
    for idx, (y, m) in enumerate(MONTHS_A):
        out: list[Entry] = []

        def add(day: int, merchant: str, amount: int, direction: str, channel: str) -> None:
            out.append(Entry(date(y, m, day), merchant, Decimal(f"{amount}.00"), direction, channel))

        add(1, "ACME TECHNOLOGIES", 60000, "credit", "neft")
        add(3, "LANDLORD RAJESH", 18000 if idx < 4 else 20000, "debit", "upi")
        add(5, "NETFLIX", 649 if idx < 5 else 799, "debit", "ecom")
        add(7, "SPOTIFY", 119, "debit", "ecom")
        add(10, "GYMFIT", 1500, "debit", "pos")
        add(12, "JIO PREPAID", 399, "debit", "upi")
        add(15, "BSES RAJDHANI", rng.randrange(1200, 1800, 10), "debit", "upi")
        for _ in range(rng.randint(6, 9)):
            add(rng.randint(1, 28), "SWIGGY", rng.randrange(150, 601, 10), "debit", "upi")
        for _ in range(rng.randint(2, 3)):
            add(rng.randint(1, 28), "ZOMATO", rng.randrange(200, 700, 10), "debit", "upi")
        for _ in range(rng.randint(1, 2)):
            add(rng.randint(1, 28), "CAFE COFFEE DAY", rng.randrange(200, 500, 10), "debit", "pos")
        for _ in range(3):
            add(rng.randint(1, 28), "BIGBASKET", rng.randrange(400, 1500, 10), "debit", "upi")
        add(rng.randint(1, 28), "DMART", rng.randrange(1000, 2500, 10), "debit", "pos")
        for _ in range(rng.randint(4, 6)):
            add(rng.randint(1, 28), "UBER INDIA", rng.randrange(120, 400, 10), "debit", "ecom")
        for _ in range(rng.randint(1, 2)):
            add(rng.randint(1, 28), "AMAZON PAY INDIA", rng.randrange(300, 3000, 10), "debit", "ecom")
        add(rng.randint(1, 28), "MYNTRA", rng.randrange(800, 2500, 10), "debit", "ecom")
        out.sort(key=lambda e: e.day)
        months.append(out)
    return months


def describe(e: Entry, n: int, style: str) -> str:
    vpa = e.merchant.lower().replace(" ", "") + "@okaxis"
    ref = str(412345000000 + 7919 * n)
    if e.channel == "upi":
        if style == "dash":
            return f"UPI-{e.merchant}-{vpa}-ICIC0000001-{ref}-Payment"
        return f"UPI/{ref}/{e.merchant}/{vpa}/Payment"
    if e.channel == "pos":
        return f"POS 4567XX1234 {e.merchant}"
    if e.channel == "ecom":
        return f"ECOM PURCHASE {e.merchant} {998000000 + 37 * n}"
    return f"NEFT-{e.merchant}"


def _balances(entries: list[Entry], start: Decimal) -> list[Decimal]:
    bal, out = start, []
    for e in entries:
        bal += e.amount if e.direction == "credit" else -e.amount
        out.append(bal)
    return out


def write_bank1(path: Path, entries: list[Entry], start: Decimal) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Narration", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"])
        for n, (e, b) in enumerate(zip(entries, _balances(entries, start))):
            dr, cr = (e.amount, "") if e.direction == "debit" else ("", e.amount)
            w.writerow([e.day.strftime("%d/%m/%Y"), describe(e, n, "dash"), dr, cr, b])


def write_bank2(path: Path, entries: list[Entry], start: Decimal) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        f.write("Account Statement for XX1234\nPeriod: Jul 2025\n\n")
        w = csv.writer(f, delimiter=";")
        w.writerow(["Txn Date", "Description", "Amount", "Dr/Cr", "Balance"])
        for n, (e, b) in enumerate(zip(entries, _balances(entries, start))):
            w.writerow([e.day.strftime("%d-%b-%Y"), describe(e, n, "slash"), f"{e.amount:,.2f}",
                        "DR" if e.direction == "debit" else "CR", f"{b:,.2f}"])


def write_bank3(path: Path, entries: list[Entry]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Transaction Date", "Details", "Amount"])
        for n, e in enumerate(entries):
            signed = e.amount if e.direction == "credit" else -e.amount
            w.writerow([e.day.isoformat(), describe(e, n, "slash"), signed])


def write_pdf(path: Path, entries: list[Entry], start: Decimal) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

        style = ParagraphStyle("c", fontSize=7, leading=9)
        head = ["Date", "Narration", "Withdrawal Amt.", "Deposit Amt.", "Balance"]
        rows = [[Paragraph(h, style) for h in head]]
        for n, (e, b) in enumerate(zip(entries, _balances(entries, start))):
            dr, cr = (f"{e.amount:,.2f}", "") if e.direction == "debit" else ("", f"{e.amount:,.2f}")
            cells = [e.day.strftime("%d/%m/%Y"), describe(e, n, "slash"), dr, cr, f"{b:,.2f}"]
            rows.append([Paragraph(c, style) for c in cells])
        table = Table(rows, colWidths=[55, 250, 65, 65, 65], repeatRows=1)
        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
        SimpleDocTemplate(str(path), pagesize=A4).build([table])
    except ImportError:
        pass


def generate(out_dir: Path, seed: int = 42) -> list[Entry]:
    """Write all synthetic files into out_dir and return the full ground-truth ledger."""
    out_dir.mkdir(parents=True, exist_ok=True)
    m = build_ledger(seed)
    bal = OPENING_BALANCE_A
    starts = []
    for month in m:
        starts.append(bal)
        bal = _balances(month, bal)[-1]
    write_bank1(out_dir / "bank1_apr_may.csv", m[0] + m[1], starts[0])
    write_bank3(out_dir / "bank3_jun.csv", m[2])
    write_bank2(out_dir / "bank2_jul.csv", m[3], starts[3])
    write_pdf(out_dir / "statement_aug.pdf", m[4], starts[4])
    (out_dir / "sms_sep.txt").write_text("\n".join(sms_text(e) for e in m[5]) + "\n", encoding="utf-8")
    return [e for month in m for e in month]


def write_outputs() -> dict:
    files_dir = Path(__file__).parent / "files"
    generate(files_dir)
    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    b = build()
    write_files(b, str(out_dir))
    with open(out_dir / "seed_data.json", "w", encoding="utf-8") as f:
        json.dump(b, f, indent=2, default=str)
    return b


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default=date.today().isoformat())
    ap.add_argument("--out", default="data/synthetic/output")
    a = ap.parse_args()
    d = build(date.fromisoformat(a.as_of))
    write_files(d, a.out)
    write_outputs()
    print(f"Synthetic outputs generated.")

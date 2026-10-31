"""Generate synthetic Indian banking data: transactions, profile, goals, subscriptions.

Run directly to write CSVs, SMS fixtures, and a JSON seed file:
    python -m data.synthetic.generate

The generated data lands in data/synthetic/output/.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import random

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

MERCHANTS: list[tuple[str, str, int, int]] = [
    # (name, category, min_amount, max_amount)
    ("Swiggy", "Food", 150, 800),
    ("Zomato", "Food", 200, 900),
    ("Dominos", "Food", 300, 750),
    ("Chai Point", "Food", 80, 250),
    ("BigBasket", "Groceries", 500, 3200),
    ("DMart", "Groceries", 800, 4500),
    ("Zepto", "Groceries", 150, 1200),
    ("Blinkit", "Groceries", 200, 1400),
    ("Uber", "Transport", 100, 650),
    ("Ola", "Transport", 90, 550),
    ("Metro Card Recharge", "Transport", 200, 500),
    ("HP Petrol Pump", "Transport", 500, 2500),
    ("Amazon", "Shopping", 350, 5500),
    ("Flipkart", "Shopping", 500, 8000),
    ("Myntra", "Shopping", 400, 3200),
    ("Netflix", "Entertainment", 199, 199),
    ("Spotify", "Entertainment", 119, 119),
    ("Hotstar", "Entertainment", 299, 299),
    ("BookMyShow", "Entertainment", 250, 750),
    ("Jio Recharge", "Bills", 239, 999),
    ("Electricity Board", "Bills", 850, 3200),
    ("Water Supply Board", "Bills", 200, 650),
    ("Indane Gas Cylinder", "Bills", 950, 1100),
    ("Apollo Pharmacy", "Health", 180, 2200),
    ("Practo Doctor Consultation", "Health", 500, 1500),
    ("Cult.fit Gym", "Health", 1500, 3000),
    ("Udemy Course", "Education", 449, 1299),
    ("Coursera", "Education", 799, 3999),
    ("MakeMyTrip", "Travel", 2500, 16000),
    ("IRCTC Train Ticket", "Travel", 350, 2800),
    ("ATM Cash Withdrawal", "ATM", 1000, 10000),
    ("UPI to Landlord", "Transfers", 18000, 18000),
]

INCOME_CREDITS = [
    ("Salary - TechCorp Solutions India", "Salary", 75000),
    ("Freelance UI Consulting", "Income", 18000),
]

SMS_TEMPLATES = [
    "INR {amount} debited from A/c XX1234 on {date} to {merchant}. Avl Bal: INR {balance}. -HDFC Bank",
    "Rs.{amount} spent on HDFC Card ending 5678 at {merchant} on {date}. Ref {ref}. If not done by you call 18002586161.",
    "Amt Sent Rs.{amount} From ICICI Bank Acc XX4567 To {merchant} On {date} Ref No {ref}",
    "Dear Customer, INR {amount} has been debited from your account XX9012 for {merchant} on {date}. Available balance: INR {balance}.",
    "SBI: Rs {amount} debited from a/c no. XX3456 on {date} for {merchant}. Your balance is Rs {balance}.",
]


def generate_transactions(
    start: dt.date = dt.date(2026, 7, 1),
    end: dt.date = dt.date(2026, 10, 15),
    seed: int = 42,
) -> list[dict]:
    """Generate realistic bank transactions covering ~3.5 months."""
    rng = random.Random(seed)
    txns: list[dict] = []
    current = start
    balance = 55000

    while current <= end:
        # Salary credit on the 1st of each month
        if current.day == 1:
            sal = INCOME_CREDITS[0]
            balance += sal[2]
            txns.append({
                "date": current.isoformat(),
                "amount": sal[2],
                "direction": "credit",
                "description": sal[0],
                "merchant": "TechCorp Solutions",
                "category": sal[1],
                "source": "csv",
                "raw_text": None,
                "balance_after": balance,
            })
            # Occasional freelance credit
            if rng.random() < 0.4:
                freelance = INCOME_CREDITS[1]
                amt = rng.randint(12000, 22000)
                balance += amt
                txns.append({
                    "date": current.isoformat(),
                    "amount": amt,
                    "direction": "credit",
                    "description": freelance[0],
                    "merchant": "Freelance Client",
                    "category": freelance[1],
                    "source": "csv",
                    "raw_text": None,
                    "balance_after": balance,
                })

        # Daily transactions
        n_txns = rng.randint(1, 4)
        for _ in range(n_txns):
            item = rng.choice(MERCHANTS)
            name, category, lo, hi = item
            amount = rng.randint(lo, hi)
            # Round amounts to whole multiples of 10
            amount = max(10, round(amount / 10) * 10)
            balance = max(0, balance - amount)
            upi_ref = f"UPI/{rng.randint(100000000000, 999999999999)}"
            desc = f"{name} {upi_ref}" if rng.random() < 0.7 else name

            txns.append({
                "date": current.isoformat(),
                "amount": amount,
                "direction": "debit",
                "description": desc,
                "merchant": name,
                "category": category,
                "source": rng.choice(["csv", "csv", "csv", "sms"]),
                "raw_text": None,
                "balance_after": balance,
            })

        current += dt.timedelta(days=1)

    return txns


def generate_sms_messages(txns: list[dict], seed: int = 42) -> list[str]:
    """Generate Indian bank SMS messages corresponding to transactions."""
    rng = random.Random(seed)
    messages = []
    for t in txns:
        if t["direction"] != "debit" or rng.random() > 0.35:
            continue
        template = rng.choice(SMS_TEMPLATES)
        msg = template.format(
            amount=t["amount"],
            date=dt.date.fromisoformat(t["date"]).strftime("%d-%m-%Y"),
            merchant=t["merchant"],
            balance=t.get("balance_after", rng.randint(15000, 75000)),
            ref=rng.randint(100000000000, 999999999999),
        )
        messages.append(msg)
    return messages


def generate_csv(txns: list[dict]) -> str:
    """Return CSV content in standard Indian bank statement format."""
    lines = ["Date,Description,Debit,Credit,Balance"]
    balance = 55000
    for t in txns:
        date_str = dt.date.fromisoformat(t["date"]).strftime("%d/%m/%Y")
        if t["direction"] == "credit":
            balance += t["amount"]
            lines.append(f"{date_str},\"{t['description']}\",,{t['amount']},{balance}")
        else:
            balance = max(0, balance - t["amount"])
            lines.append(f"{date_str},\"{t['description']}\",{t['amount']},,{balance}")
    return "\n".join(lines)


def generate_profile() -> dict:
    return {
        "monthly_income": 75000,
        "fixed_costs": {
            "rent": 18000,
            "insurance": 2500,
            "wifi & utilities": 1500,
            "bike emi": 4500,
        },
        "emergency_fund_current": 50000,
        "emergency_fund_target": 250000,
    }


def generate_goals() -> list[dict]:
    return [
        {
            "name": "Japan Autumn Trip",
            "target_amount": 180000,
            "current_amount": 40000,
            "target_date": "2027-10-01",
            "priority": 1,
        },
        {
            "name": "MacBook Pro Upgrade",
            "target_amount": 120000,
            "current_amount": 25000,
            "target_date": "2027-04-01",
            "priority": 2,
        },
        {
            "name": "Executive Certification",
            "target_amount": 35000,
            "current_amount": 10000,
            "target_date": None,
            "priority": 3,
        },
    ]


def generate_recurring() -> list[dict]:
    return [
        {
            "merchant": "Netflix",
            "amount": 199,
            "cadence": "monthly",
            "last_seen": "2026-10-01",
            "next_expected": "2026-11-01",
            "status": "active",
        },
        {
            "merchant": "Spotify",
            "amount": 119,
            "cadence": "monthly",
            "last_seen": "2026-10-05",
            "next_expected": "2026-11-05",
            "status": "active",
        },
        {
            "merchant": "Hotstar",
            "amount": 299,
            "cadence": "monthly",
            "last_seen": "2026-09-15",
            "next_expected": "2026-10-15",
            "status": "active",
        },
        {
            "merchant": "Cult.fit Gym",
            "amount": 1500,
            "cadence": "monthly",
            "last_seen": "2026-10-01",
            "next_expected": "2026-11-01",
            "status": "active",
        },
        {
            "merchant": "Jio Recharge",
            "amount": 239,
            "cadence": "monthly",
            "last_seen": "2026-09-28",
            "next_expected": "2026-10-28",
            "status": "changed",
        },
    ]


def write_outputs() -> dict:
    """Generate all datasets and write them to data/synthetic/output/."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    txns = generate_transactions()
    sms = generate_sms_messages(txns)

    # 1. Bank statement CSV
    csv_path = os.path.join(OUTPUT_DIR, "bank_statement.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        f.write(generate_csv(txns))

    # 2. SMS log text
    sms_path = os.path.join(OUTPUT_DIR, "sms_messages.txt")
    with open(sms_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sms))

    # 3. Master JSON fixture for DB seeding
    seed_payload = {
        "transactions": txns,
        "profile": generate_profile(),
        "goals": generate_goals(),
        "recurring": generate_recurring(),
    }
    json_path = os.path.join(OUTPUT_DIR, "seed_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(seed_payload, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(txns)} transactions and {len(sms)} SMS messages in {OUTPUT_DIR}")
    return seed_payload


if __name__ == "__main__":
    write_outputs()

from datetime import date
from decimal import Decimal

import pytest

from ingest.csv_parser import parse_csv
from ingest.normalizer import clean_merchant, dedupe, keys_for, parse_amount, parse_date
from ingest.sms_parser import parse_sms, parse_sms_batch

BANK1 = """Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance
01/10/2025,UPI-SWIGGY-swiggy@icici-ICIC0000001-412345678901-Payment,450.00,,24550.00
05/10/2025,NEFT-ACME CORP SALARY,,60000.00,84550.00
Total,,450.00,60000.00,
"""
BANK2 = """Account Statement for XX1234
Period: Oct 2025

Txn Date;Description;Amount;Dr/Cr;Balance
12-Oct-2025;POS 4567XX1234 AMAZON PAY INDIA;1,299.00;DR;10,000.00
13-Oct-2025;INTEREST CREDIT;12.50;CR;10,012.50
"""
BANK3 = """Transaction Date,Details,Amount
2025-10-02,UPI/412345678901/NETFLIX/netflix@axis/Payment,-649.00
2025-10-03,Refund Myntra,(0.00)
2025-10-04,Cash deposit,2000
"""


def test_csv_two_column_layout():
    t = parse_csv(BANK1, account="HDFC")
    assert [x.direction for x in t] == ["debit", "credit"]
    assert t[0].date == date(2025, 10, 1) and t[0].amount == Decimal("450.00")
    assert t[0].merchant == "SWIGGY" and t[0].balance == Decimal("24550.00")


def test_csv_preamble_semicolon_and_type_column():
    t = parse_csv(BANK2.encode())
    assert len(t) == 2
    assert t[0].merchant == "AMAZON PAY INDIA" and t[0].amount == Decimal("1299.00")
    assert t[1].direction == "credit"


def test_csv_signed_amount_and_unsigned_ambiguous_row():
    t = parse_csv(BANK3)
    assert t[0].direction == "debit" and t[0].amount == Decimal("649.00")
    assert t[0].merchant == "NETFLIX"
    assert len(t) == 2 and t[1].direction == "credit"  # zero-amount row skipped


def test_csv_no_header_raises():
    with pytest.raises(ValueError):
        parse_csv("foo,bar\n1,2\n")


@pytest.mark.parametrize("text,expected", [
    ("2025-10-01", date(2025, 10, 1)), ("01/10/2025", date(2025, 10, 1)),
    ("12-Oct-25", date(2025, 10, 12)), ("3 Nov 2025", date(2025, 11, 3)),
])
def test_parse_date(text, expected):
    assert parse_date(text) == expected


def test_parse_date_default_year_and_garbage():
    assert parse_date("12-Oct", default_year=2025) == date(2025, 10, 12)
    with pytest.raises(ValueError):
        parse_date("not a date")


@pytest.mark.parametrize("text,expected", [
    ("1,234.50", "1234.50"), ("Rs. 450", "450"), ("(200.00)", "-200.00"), ("300 Dr", "-300"),
])
def test_parse_amount(text, expected):
    assert parse_amount(text) == Decimal(expected)


@pytest.mark.parametrize("desc,expected", [
    ("UPI/412345678901/Zomato/zomato@hdfc/Payment", "ZOMATO"),
    ("UPI-SWIGGY-swiggy@icici-ICIC0000001-412345678901-Payment", "SWIGGY"),
    ("POS 4567XX1234 AMAZON PAY INDIA", "AMAZON PAY INDIA"),
    ("ECOM PURCHASE UBER INDIA 998877665", "UBER INDIA"),
])
def test_clean_merchant(desc, expected):
    assert clean_merchant(desc) == expected


def test_sms_debit():
    t = parse_sms("Rs.450.00 debited from A/c XX1234 at SWIGGY on 12-Oct. Avl bal Rs.5000", 2025)
    assert t.direction == "debit" and t.amount == Decimal("450.00")
    assert t.merchant == "SWIGGY" and t.date == date(2025, 10, 12) and t.account == "XX1234"


def test_sms_credit_and_unmatched():
    t = parse_sms("INR 1,200.00 credited to A/c XX1234 on 05-Oct-25 by RAHUL", 2025)
    assert t.direction == "credit" and t.amount == Decimal("1200.00") and t.merchant == "RAHUL"
    parsed, unmatched = parse_sms_batch(
        "Rs 250 spent on card XX9999 at UBER on 10-10-2025\n\nYour OTP is 123456\n", 2025)
    assert len(parsed) == 1 and unmatched == ["Your OTP is 123456"]


def test_dedupe_keeps_same_day_twins_but_drops_reupload():
    csv_text = "Date,Description,Debit\n01/10/2025,CHAI POINT,50\n01/10/2025,CHAI POINT,50\n"
    first = parse_csv(csv_text)
    assert len(dedupe(first)) == 2
    assert dedupe(parse_csv(csv_text), keys_for(first)) == []

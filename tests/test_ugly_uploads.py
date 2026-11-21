"""Deliberately ugly statements: odd dates, preamble lines, signed/unicode-minus amounts, and friendly errors."""
from pathlib import Path

import pytest

from ingest.csv_parser import parse_csv
from ingest.service import UnsupportedFile, ingest_file

UGLY = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "ugly"


def _rows(name):
    return [(t.date.isoformat(), t.direction, int(t.amount), t.merchant) for t in parse_csv((UGLY / name).read_bytes())]


def test_preamble_odd_dates_brackets_and_footer():
    assert _rows("ugly_1_preamble_odd_dates.csv") == [
        ("2026-10-01", "credit", 75000, "SALARY ACME TECHNOLOGIES"),
        ("2026-10-05", "debit", 420, "SWIGGY"),
        ("2026-10-07", "debit", 310, "ZOMATO"),
        ("2026-10-09", "debit", 1299, "AMAZON"),
    ]


def test_signed_amounts_with_unicode_minus_and_dr_cr_suffix():
    rows = _rows("ugly_2_signed_unicode_minus.csv")
    assert ("2026-10-04", "debit", 18000, "LANDLORD RAJESH") in rows  # U+2212 minus must not turn rent into income
    assert [r[1] for r in rows] == ["credit", "debit", "debit", "debit", "credit"]


def test_not_a_statement_gives_a_friendly_message():
    with pytest.raises(ValueError, match="doesn't look like a bank statement"):
        parse_csv((UGLY / "ugly_3_not_a_statement.csv").read_bytes())


def test_header_but_unreadable_rows_and_unsupported_type_are_friendly():
    with pytest.raises(ValueError, match="couldn't read any rows"):
        parse_csv("Date,Narration,Amount\nsomeday,Coffee,abc\n")
    with pytest.raises(UnsupportedFile, match="Paste SMS alerts"):
        ingest_file("photo.png", b"x")

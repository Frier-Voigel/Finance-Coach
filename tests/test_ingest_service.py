import json
from datetime import date
from decimal import Decimal

import pytest

from ingest import llm_fallback
from ingest.llm_fallback import extract_with_llm
from ingest.normalizer import keys_for
from ingest.pdf_parser import parse_tables
from ingest.service import UnsupportedFile, ingest_file, ingest_sms

CSV = b"Date,Description,Debit,Credit\n01/10/2025,UPI/1234567890/ZOMATO/z@h/Pay,300,\n"


def test_pdf_tables_parsed_and_junk_table_skipped():
    good = [["Date", "Narration", "Debit", "Credit"], ["01-10-2025", "POS AMAZON", "500.00", None]]
    junk = [["Page", "1 of 2"]]
    t = parse_tables([junk, good])
    assert len(t) == 1 and t[0].source == "pdf" and t[0].amount == Decimal("500.00")


def test_ingest_file_csv_and_reupload_deduped():
    first = ingest_file("a.csv", CSV)
    assert len(first.transactions) == 1 and first.transactions[0].merchant == "ZOMATO"
    again = ingest_file("a.csv", CSV, existing_keys=keys_for(first.transactions))
    assert again.transactions == [] and again.duplicates_skipped == 1


def test_unsupported_file():
    with pytest.raises(UnsupportedFile):
        ingest_file("notes.txt", b"hi")


def test_sms_llm_fallback_and_cache():
    llm_fallback._CACHE.clear()
    calls = []

    def fake(prompt):
        calls.append(prompt)
        return "```json\n" + json.dumps([
            {"date": "14 Oct", "description": "Paid to CHAI POINT", "amount": "Rs 80", "direction": "debit"},
            {"date": "bad", "description": "x", "amount": "1", "direction": "debit"},
            {"date": "14 Oct", "description": "x", "amount": "1", "direction": "sideways"},
        ]) + "\n```"

    r = ingest_sms("Rs.450.00 debited from A/c XX1234 at SWIGGY on 12-Oct\nweird msg", 2025, fake)
    assert len(r.transactions) == 2 and r.unparsed == []
    assert r.transactions[1].amount == Decimal("80") and r.transactions[1].date == date(2025, 10, 14)
    extract_with_llm("weird msg", "sms", fake, 2025)
    assert len(calls) == 1  # second call served from cache


def test_sms_without_llm_reports_unparsed_and_bad_llm_json_is_ignored():
    r = ingest_sms("Your OTP is 1", 2025)
    assert r.transactions == [] and r.unparsed == ["Your OTP is 1"]
    llm_fallback._CACHE.clear()
    assert extract_with_llm("zzz", "sms", lambda p: "not json") == []

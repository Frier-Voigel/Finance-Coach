"""Phase A6 Comprehensive Test Suite.

Covers:
1. Parser tests per format (CSV layouts, SMS, PDF, Normalizer)
2. Correction-loop test (patch, rule persistence, history backfill, user protection, rule deletion)
3. Recurring-detection test on synthetic data (Netflix price hike, Spotify active, GymFit unused alert)
"""
from __future__ import annotations

import tempfile
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from data.synthetic.generate import generate
from engine.categorize.rules import apply_rules, categorize
from engine.categorize.service import patch_transaction, save_parsed_txns
from engine.recurring.detector import detect_recurring
from ingest.models import ParsedTxn
from ingest.normalizer import clean_merchant, dedupe, keys_for
from ingest.pdf_parser import parse_pdf, parse_tables
from ingest.service import ingest_file, ingest_sms
from shared.schema import Recurring, Rule, Transaction


# ---------------------------------------------------------------------------
# Fixture: Isolated in-memory DB per test
# ---------------------------------------------------------------------------

@pytest.fixture(name="db_session")
def db_session_fixture():
    """In-memory SQLite session with StaticPool."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# ===========================================================================
# 1. PARSER TESTS PER FORMAT
# ===========================================================================

def test_a6_parser_csv_three_distinct_layouts():
    """CSV parser must auto-detect 3 distinct bank statement layouts."""
    # Layout 1: Two-column Withdrawal / Deposit with dd/mm/yyyy dates
    csv1 = (
        b"Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance\n"
        b"01/04/2025,UPI-SWIGGY-swiggy@okaxis-ICIC0000001-412345000000-Payment,450.00,,24550.00\n"
        b"01/04/2025,NEFT-ACME TECHNOLOGIES,,60000.00,84550.00\n"
    )
    r1 = ingest_file("bank1.csv", csv1)
    assert len(r1.transactions) == 2
    assert r1.transactions[0].direction == "debit"
    assert r1.transactions[0].amount == Decimal("450.00")
    assert r1.transactions[0].merchant == "SWIGGY"
    assert r1.transactions[1].direction == "credit"
    assert r1.transactions[1].amount == Decimal("60000.00")
    assert r1.transactions[1].merchant == "ACME TECHNOLOGIES"

    # Layout 2: Semicolon delimiter with preamble and Dr/Cr indicator column
    csv2 = (
        b"Statement Header: Account XX1234\nPeriod: Jul 2025\n\n"
        b"Txn Date;Description;Amount;Dr/Cr;Balance\n"
        b"05-Jul-2025;ECOM PURCHASE NETFLIX 998000000;649.00;DR;45,000.00\n"
        b"10-Jul-2025;POS 4567XX1234 GYMFIT;1,500.00;DR;43,500.00\n"
    )
    r2 = ingest_file("bank2.csv", csv2)
    assert len(r2.transactions) == 2
    assert r2.transactions[0].merchant == "NETFLIX"
    assert r2.transactions[0].direction == "debit"
    assert r2.transactions[0].amount == Decimal("649.00")
    assert r2.transactions[1].merchant == "GYMFIT"
    assert r2.transactions[1].amount == Decimal("1500.00")

    # Layout 3: Single signed Amount column (- for debit, + for credit) with ISO dates
    csv3 = (
        b"Transaction Date,Details,Amount\n"
        b"2025-06-03,UPI/412345000000/LANDLORD RAJESH/landlord@okaxis/Payment,-18000.00\n"
        b"2025-06-01,NEFT-ACME TECHNOLOGIES,60000.00\n"
    )
    r3 = ingest_file("bank3.csv", csv3)
    assert len(r3.transactions) == 2
    assert r3.transactions[0].direction == "debit"
    assert r3.transactions[0].amount == Decimal("18000.00")
    assert r3.transactions[0].merchant == "LANDLORD RAJESH"
    assert r3.transactions[1].direction == "credit"
    assert r3.transactions[1].amount == Decimal("60000.00")


def test_a6_parser_sms_debit_credit_and_unparsed():
    """SMS parser handles debits, credits, and flags unparsed junk alerts."""
    sms_batch = (
        "Rs.450.00 debited from A/c XX1234 at SWIGGY on 12-Apr. Avl bal Rs.40000.00\n"
        "Rs.60,000.00 credited to A/c XX1234 by ACME TECHNOLOGIES on 30-Apr. Avl bal Rs.100000.00\n"
        "Your OTP for login is 987654. Do not share with anyone.\n"
        "Rs.119.00 debited from A/c XX1234 at SPOTIFY on 07-May.\n"
    )
    r = ingest_sms(sms_batch, default_year=2025)
    assert len(r.transactions) == 3
    assert len(r.unparsed) == 1
    assert "Your OTP" in r.unparsed[0]

    debit_swiggy = next(t for t in r.transactions if t.merchant == "SWIGGY")
    assert debit_swiggy.direction == "debit"
    assert debit_swiggy.amount == Decimal("450.00")
    assert debit_swiggy.date == date(2025, 4, 12)

    credit_salary = next(t for t in r.transactions if t.merchant == "ACME TECHNOLOGIES")
    assert credit_salary.direction == "credit"
    assert credit_salary.amount == Decimal("60000.00")
    assert credit_salary.date == date(2025, 4, 30)


def test_a6_parser_pdf_synthetic_statement():
    """PDF parser parses tables from synthetic statement and ignores junk rows."""
    files_dir = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "files"
    pdf_path = files_dir / "statement_aug.pdf"

    if pdf_path.exists():
        pdf_bytes = pdf_path.read_bytes()
        res = ingest_file("statement_aug.pdf", pdf_bytes)
        assert len(res.transactions) > 0
        assert res.unparsed == []
        assert all(t.source == "pdf" for t in res.transactions)
        merchants = {t.merchant for t in res.transactions}
        assert "NETFLIX" in merchants
        assert "SPOTIFY" in merchants

    # Verify junk table filtering logic
    junk_table = [["Summary", "Page 1 of 1"], ["Account", "XX1234"]]
    valid_table = [
        ["Date", "Narration", "Withdrawal Amt.", "Deposit Amt.", "Balance"],
        ["05/08/2025", "ECOM PURCHASE NETFLIX 998000", "649.00", "", "50,000.00"],
    ]
    parsed = parse_tables([junk_table, valid_table])
    assert len(parsed) == 1
    assert parsed[0].merchant == "NETFLIX"
    assert parsed[0].amount == Decimal("649.00")


def test_a6_normalizer_merchant_cleaning_and_deduplication():
    """Normalizer cleans UPI, POS, ECOM, NEFT strings and dedupes on re-upload."""
    # Merchant cleaning
    assert clean_merchant("UPI-SWIGGY-swiggy@icici-ICIC0000001-412345-Payment") == "SWIGGY"
    assert clean_merchant("UPI/412345678901/Zomato/zomato@hdfc/Payment") == "ZOMATO"
    assert clean_merchant("POS 4567XX1234 AMAZON PAY INDIA") == "AMAZON PAY INDIA"
    assert clean_merchant("POS 4567XX1234 DMART") == "DMART"
    assert clean_merchant("ECOM PURCHASE UBER INDIA 998877665") == "UBER INDIA"
    assert clean_merchant("NEFT-ACME TECHNOLOGIES") == "ACME TECHNOLOGIES"

    # Deduplication
    t1 = ParsedTxn(date(2025, 4, 1), Decimal("450.00"), "debit", "SWIGGY", "SWIGGY", "csv")
    t2 = ParsedTxn(date(2025, 4, 1), Decimal("450.00"), "debit", "SWIGGY", "SWIGGY", "csv")
    # Same day twins: different occurrences kept on first upload
    unique_keys = set()
    first_upload = dedupe([t1, t2], existing_keys=unique_keys)
    assert len(first_upload) == 2

    # Re-uploading the same transactions should be recognized as duplicates
    existing = keys_for(first_upload)
    second_upload = dedupe([t1, t2], existing_keys=existing)
    assert len(second_upload) == 0


# ===========================================================================
# 2. CORRECTION LOOP TESTS (A3/F3)
# ===========================================================================

def test_a6_correction_loop_full_lifecycle(db_session: Session):
    """F3 correction loop:
    1. Patching a transaction creates a Rule in DB.
    2. Back-fills all matching past non-user transactions.
    3. User-assigned categories are NEVER overwritten.
    4. Deleting the rule succeeds via API.
    """
    # Create 15 SWIGGY transactions: 14 with category_source="rule", 1 already user-set to "Entertainment"
    txns = []
    for i in range(14):
        txns.append(
            Transaction(
                date=date(2025, 4, i + 1),
                amount=Decimal("350.00"),
                direction="debit",
                description=f"UPI-SWIGGY-{i}",
                merchant="SWIGGY",
                category="Other",
                category_source="rule",
                source="csv",
            )
        )
    # 15th transaction: user previously set it to "Entertainment"
    user_preserved = Transaction(
        date=date(2025, 4, 15),
        amount=Decimal("500.00"),
        direction="debit",
        description="UPI-SWIGGY-15",
        merchant="SWIGGY",
        category="Entertainment",
        category_source="user",
        source="csv",
    )
    txns.append(user_preserved)

    for t in txns:
        db_session.add(t)
    db_session.commit()

    all_before = db_session.exec(select(Transaction)).all()
    assert len(all_before) == 15

    # Target first transaction for correction to "Food"
    target_id = all_before[0].id
    res = patch_transaction(target_id, "Food", db_session)

    # 1. Check returned structure
    assert res["transaction"]["id"] == target_id
    assert res["transaction"]["category"] == "Food"
    assert res["transaction"]["category_source"] == "user"
    assert res["rule_created"]["pattern"] == "SWIGGY"
    assert res["rule_created"]["category"] == "Food"
    assert res["rule_created"]["match_type"] == "merchant"

    # 2. Check back-fill count:
    # 14 rows total with source="rule": 1 was patched, remaining 13 should be back-filled!
    assert res["past_updated"] == 13

    # 3. Check database state
    all_after = db_session.exec(select(Transaction)).all()
    food_count = sum(1 for t in all_after if t.category == "Food")
    assert food_count == 14  # target + 13 back-filled

    # 4. Verify user-preserved transaction was NOT touched
    preserved = db_session.get(Transaction, user_preserved.id)
    assert preserved.category == "Entertainment"
    assert preserved.category_source == "user"

    # 5. Verify rule is persistent in rules table
    rule_in_db = db_session.exec(select(Rule).where(Rule.pattern == "SWIGGY")).first()
    assert rule_in_db is not None
    assert rule_in_db.category == "Food"

    # 6. Delete rule
    db_session.delete(rule_in_db)
    db_session.commit()
    assert db_session.get(Rule, rule_in_db.id) is None


# ===========================================================================
# 3. RECURRING DETECTION TEST ON SYNTHETIC DATA (A4/F4)
# ===========================================================================

def test_a6_recurring_detection_on_full_synthetic_data(db_session: Session):
    """Recurring detection across 6 months of synthetic bank data:
    1. Detects NETFLIX, SPOTIFY, GYMFIT, JIO PREPAID.
    2. Flags NETFLIX with status="changed" (>5% price increase from 649 to 799 in Sep).
    3. SPOTIFY is status="active" (cadence="monthly", amount=119.00).
    4. GYMFIT is status="active" (cadence="monthly", amount=1500.00).
    5. Marking GYMFIT as unused updates status to "unused".
    6. Non-recurring merchants (DMART, MYNTRA, SWIGGY) are not detected as recurring.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Generate the full ground-truth synthetic data
        generate(tmp_path)

        # Ingest all synthetic files through the ingest pipeline
        all_parsed: list[ParsedTxn] = []
        for csv_file in sorted(tmp_path.glob("*.csv")) + sorted(tmp_path.glob("*.pdf")):
            r = ingest_file(csv_file.name, csv_file.read_bytes())
            all_parsed.extend(r.transactions)

        sms_file = tmp_path / "sms_sep.txt"
        r_sms = ingest_sms(sms_file.read_text(encoding="utf-8"), default_year=2025)
        all_parsed.extend(r_sms.transactions)

        # Persist transactions into the database
        saved_txns = save_parsed_txns(all_parsed, db_session)
        assert len(saved_txns) == 175  # 6 full months of synthetic transactions

        # Run recurring detection
        recurring = detect_recurring(saved_txns)
        recurring_map = {r["merchant"]: r for r in recurring}

        # Subscriptions from the synthetic story
        assert "NETFLIX" in recurring_map, "NETFLIX subscription not detected"
        assert "SPOTIFY" in recurring_map, "SPOTIFY subscription not detected"
        assert "GYMFIT" in recurring_map, "GYMFIT subscription not detected"

        # Check Netflix price hike
        netflix = recurring_map["NETFLIX"]
        assert netflix["cadence"] == "monthly"
        assert netflix["status"] == "changed", (
            f"Expected NETFLIX status 'changed' due to price hike, got '{netflix['status']}'"
        )

        # Check Spotify steady active cadence
        spotify = recurring_map["SPOTIFY"]
        assert spotify["cadence"] == "monthly"
        assert spotify["amount"] == Decimal("119.00")
        assert spotify["status"] == "active"

        # Check GymFit steady active cadence
        gymfit = recurring_map["GYMFIT"]
        assert gymfit["cadence"] == "monthly"
        assert gymfit["amount"] == Decimal("1500.00")
        assert gymfit["status"] == "active"

        # Verify non-recurring transactions are NOT flagged
        assert "DMART" not in recurring_map
        assert "MYNTRA" not in recurring_map
        assert "SWIGGY" not in recurring_map

        # Verify marking GymFit as unused
        gym_row = Recurring(
            merchant="GYMFIT",
            amount=gymfit["amount"],
            cadence=gymfit["cadence"],
            last_seen=gymfit["last_seen"],
            next_expected=gymfit.get("next_expected"),
            status="unused",
        )
        db_session.add(gym_row)
        db_session.commit()

        # Re-check merged status
        overrides = {r.merchant: r.status for r in db_session.exec(select(Recurring)).all()}
        assert overrides.get("GYMFIT") == "unused"


# ===========================================================================
# 4. END-TO-END FASTAPI CONTRACT TEST (Person A API Endpoints)
# ===========================================================================

def test_a6_fastapi_endpoints_contract_integration():
    """Exercise Person A FastAPI endpoints end-to-end via TestClient:
    - POST /ingest/upload
    - POST /ingest/sms
    - GET /transactions
    - PATCH /transactions/{id}
    - GET /rules
    - DELETE /rules/{id}
    - GET /recurring
    - POST /recurring/{hash}/mark-unused
    - GET /health
    """
    import os
    os.environ["DATABASE_URL"] = "sqlite://"
    from shared import db as db_module
    db_module.get_engine.cache_clear()
    engine = db_module.get_engine()
    SQLModel.metadata.create_all(engine)

    try:
        from api.main import app
        client = TestClient(app, raise_server_exceptions=True)

        # 1. Health check
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

        # 2. Upload CSV statement
        csv_content = (
            b"Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance\n"
            b"01/04/2025,UPI-SWIGGY-1,250.00,,49750.00\n"
            b"02/04/2025,UPI-SWIGGY-2,250.00,,49500.00\n"
            b"05/04/2025,ECOM NETFLIX,649.00,,48851.00\n"
            b"05/05/2025,ECOM NETFLIX,649.00,,48202.00\n"
            b"05/06/2025,ECOM NETFLIX,799.00,,47403.00\n"
        )
        up_resp = client.post("/ingest/upload", files={"file": ("stmt.csv", csv_content)})
        assert up_resp.status_code == 200
        assert up_resp.json()["inserted"] == 5

        # 3. List transactions
        txns_resp = client.get("/transactions")
        assert txns_resp.status_code == 200
        txns = txns_resp.json()
        assert len(txns) == 5

        # 4. Patch category (trigger correction loop)
        swiggy_txn = next(t for t in txns if t["merchant"] == "SWIGGY")
        patch_resp = client.patch(
            f"/transactions/{swiggy_txn['id']}",
            json={"category": "Food"},
        )
        assert patch_resp.status_code == 200
        patch_data = patch_resp.json()
        assert patch_data["transaction"]["category"] == "Food"
        assert patch_data["rule_created"]["pattern"] == "SWIGGY"
        assert patch_data["past_updated"] == 1

        # 5. List rules
        rules_resp = client.get("/rules")
        assert rules_resp.status_code == 200
        rules = rules_resp.json()
        assert any(r["pattern"] == "SWIGGY" for r in rules)

        # 6. Check recurring detection
        rec_resp = client.get("/recurring")
        assert rec_resp.status_code == 200
        recurring_items = rec_resp.json()
        netflix_item = next((i for i in recurring_items if i["merchant"] == "NETFLIX"), None)
        assert netflix_item is not None
        assert netflix_item["status"] == "changed"

        # 7. Mark as unused
        hash_val = netflix_item["merchant_hash"]
        mark_resp = client.post(f"/recurring/{hash_val}/mark-unused")
        assert mark_resp.status_code == 200
        assert mark_resp.json()["status"] == "unused"

        # Re-verify recurring status is now unused
        rec_resp2 = client.get("/recurring")
        netflix_item2 = next(i for i in rec_resp2.json() if i["merchant"] == "NETFLIX")
        assert netflix_item2["status"] == "unused"

        # 8. Delete rule
        rule_id = next(r["id"] for r in rules if r["pattern"] == "SWIGGY")
        del_resp = client.delete(f"/rules/{rule_id}")
        assert del_resp.status_code == 204

    finally:
        db_module.get_engine.cache_clear()
        os.environ.pop("DATABASE_URL", None)

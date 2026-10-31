import tempfile
from collections import Counter
from pathlib import Path

import pytest

from data.synthetic.generate import generate
from ingest.normalizer import keys_for
from ingest.service import ingest_file, ingest_sms


def _ingest_all(out: Path, existing=None):
    txns = []
    for f in sorted(out.glob("*.csv")) + sorted(out.glob("*.pdf")):
        r = ingest_file(f.name, f.read_bytes(), existing_keys=existing)
        assert r.unparsed == [], f.name
        txns += r.transactions
    r = ingest_sms((out / "sms_sep.txt").read_text(encoding="utf-8"), 2025, existing_keys=existing)
    assert r.unparsed == []
    return txns + r.transactions


def _sig(day, amount, direction, merchant):
    return (day, amount, direction, merchant)


def test_every_generated_row_round_trips_through_all_formats():
    with tempfile.TemporaryDirectory() as d:
        ledger = generate(Path(d))
        txns = _ingest_all(Path(d))
    want = Counter(_sig(e.day, e.amount, e.direction, e.merchant) for e in ledger)
    got = Counter(_sig(t.date, t.amount, t.direction, t.merchant) for t in txns)
    assert got == want
    assert {t.source for t in txns} == {"csv", "pdf", "sms"}


def test_story_data_present_and_reupload_adds_nothing():
    with tempfile.TemporaryDirectory() as d:
        generate(Path(d))
        txns = _ingest_all(Path(d))
        netflix = sorted({t.amount for t in txns if t.merchant == "NETFLIX"})
        rent = sorted({t.amount for t in txns if t.merchant == "LANDLORD RAJESH"})
        assert [int(a) for a in netflix] == [649, 799] and [int(a) for a in rent] == [18000, 20000]
        assert _ingest_all(Path(d), keys_for(txns)) == []


def test_upload_and_sms_endpoints():
    pytest.importorskip("httpx")
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from ingest import router as r

    app = fastapi.FastAPI()
    app.include_router(r.router)
    r.repository = r.InMemoryRepository()
    c = TestClient(app)
    csv_bytes = b"Date,Description,Debit\n01/10/2025,UPI/1234567890/ZOMATO/z@h/Pay,300\n"
    ok = c.post("/ingest/upload", files={"file": ("a.csv", csv_bytes)})
    assert ok.status_code == 200 and ok.json()["inserted"] == 1
    assert c.post("/ingest/upload", files={"file": ("a.csv", csv_bytes)}).json()["duplicates_skipped"] == 1
    bad = c.post("/ingest/upload", files={"file": ("a.txt", b"x")})
    assert bad.status_code == 415 and bad.json()["error"] == "unsupported_file"
    empty = c.post("/ingest/sms", json={"messages": "  "})
    assert empty.status_code == 422 and empty.json()["error"] == "empty_input"
    sms = c.post("/ingest/sms", json={"messages": "Rs.50.00 debited from A/c XX1 at CHAI on 01-Oct-25", "default_year": 2025})
    assert sms.json()["inserted"] == 1

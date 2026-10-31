"""DB rows and parsed rows must make the same dedupe key, or re-uploading a statement duplicates it."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from ingest.normalizer import dedupe, keys_for, txn_key


def _row(amount, account):
    return SimpleNamespace(date=date(2025, 4, 5), amount=amount, direction="debit", merchant="NETFLIX", account=account)


def test_equivalent_amounts_and_empty_account_give_one_key():
    assert txn_key(_row(Decimal("649"), "")) == txn_key(_row(Decimal("649.00"), None)) == txn_key(_row(Decimal("649.0"), ""))
    assert txn_key(_row(Decimal("600"), "")) != txn_key(_row(Decimal("60"), ""))


def test_reupload_against_db_style_rows_is_deduped():
    db_rows = [_row(Decimal("649.00"), None)]
    parsed = [_row(Decimal("649"), "")]
    assert dedupe(parsed, keys_for(db_rows)) == []
    assert dedupe(parsed + parsed, keys_for(db_rows)) == [parsed[0]]  # a genuine second identical charge survives

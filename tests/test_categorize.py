"""A2/A3 categorisation and correction-loop tests."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from shared.schema import Rule, Transaction
from engine.categorize.rules import apply_rules, categorize
from engine.categorize.service import patch_transaction, save_parsed_txns
from ingest.models import ParsedTxn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="session")
def session_fixture():
    """In-memory SQLite session, fresh per test."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


# ---------------------------------------------------------------------------
# A2 – rule engine priority
# ---------------------------------------------------------------------------

def test_rule_engine_priority(session):
    """Merchant match must win over contains, which must win over regex."""
    rules = [
        Rule(pattern="SWIGGY", match_type="merchant", category="Food"),
        Rule(pattern="NETFLIX", match_type="contains", category="Entertainment"),
        Rule(pattern=r"\bNETFLIX\b", match_type="regex", category="Other"),
    ]
    # Merchant rule wins for SWIGGY
    assert apply_rules("SWIGGY", "UPI SWIGGY Payment", rules) == "Food"

    # Contains rule wins for NETFLIX (no merchant rule for NETFLIX)
    assert apply_rules("NETFLIX", "ECOM PURCHASE NETFLIX 99012", rules) == "Entertainment"

    # Regex would match but contains wins first for NETFLIX
    result = apply_rules("NETFLIX", "ECOM PURCHASE NETFLIX 99012", rules)
    assert result == "Entertainment"

    # Only regex matches an unknown merchant
    regex_only = [Rule(pattern=r"PRIME\d+", match_type="regex", category="Shopping")]
    assert apply_rules("AMAZON", "PRIME123 ORDER", regex_only) == "Shopping"


def test_merchant_defaults_used_when_no_rule(session):
    """SWIGGY with no DB rules should categorise via MERCHANT_DEFAULTS."""
    cat, source = categorize("SWIGGY", "UPI SWIGGY PAY", [])
    assert cat == "Food"
    assert source == "rule"


def test_llm_fallback_called_for_unknown():
    """Unknown merchant with no rules should call the LLM and cache the result."""
    calls: list[str] = []

    def mock_llm(prompt: str) -> str:
        calls.append(prompt)
        return "Health"

    cat, source = categorize("WEIRD GYM XYZ", "POS WEIRD GYM XYZ", [], llm=mock_llm)
    assert cat == "Health"
    assert source == "llm"
    assert len(calls) == 1

    # Second call with same input must use cache → no new LLM call
    cat2, source2 = categorize("WEIRD GYM XYZ", "POS WEIRD GYM XYZ", [], llm=mock_llm)
    assert cat2 == "Health"
    assert len(calls) == 1  # still 1


# ---------------------------------------------------------------------------
# A3 – correction loop
# ---------------------------------------------------------------------------

def test_correction_loop(session):
    """patch_transaction must create a rule and back-fill 4 past transactions."""
    # Insert 5 SWIGGY transactions with category_source="rule"
    for i in range(5):
        t = Transaction(
            date=date(2025, 4, i + 1),
            amount=Decimal("250.00"),
            direction="debit",
            description="UPI SWIGGY payment",
            merchant="SWIGGY",
            category="Other",
            category_source="rule",
            source="csv",
        )
        session.add(t)
    session.commit()

    txns = session.exec(select(Transaction)).all()
    assert len(txns) == 5

    # Patch the first transaction to "Food"
    first_id = txns[0].id
    result = patch_transaction(first_id, "Food", session)

    # Rule was created
    assert result["rule_created"]["pattern"] == "SWIGGY"
    assert result["rule_created"]["category"] == "Food"
    assert result["rule_created"]["match_type"] == "merchant"

    # past_updated == 4 (the other 4 non-user transactions)
    assert result["past_updated"] == 4

    # All 5 should now be "Food"
    all_txns = session.exec(select(Transaction)).all()
    for t in all_txns:
        assert t.category == "Food"

    # The patched one is "user", the rest are "rule"
    patched = next(t for t in all_txns if t.id == first_id)
    assert patched.category_source == "user"

    others = [t for t in all_txns if t.id != first_id]
    for t in others:
        assert t.category_source == "rule"

"""What leaves the server for Gemini: masked identifiers, merchant-only categorisation, no statement headers."""
from ingest.llm_fallback import extract_with_llm, txn_lines
from shared.privacy import mask


def test_mask_hides_identifiers_but_keeps_amounts_and_dates():
    text = "UPI/412345007919/SWIGGY/swiggy@okaxis/Payment POS 4567XX1234 call 98765 43210 A/c XX1234 acct 123456789012"
    out = mask(text)
    for secret in ("412345007919", "swiggy@okaxis", "4567XX1234", "98765 43210", "XX1234", "123456789012"):
        assert secret not in out
    assert "SWIGGY" in out
    assert mask("05/10/2026 debited Rs. 1,25,000.00") == "05/10/2026 debited Rs. 1,25,000.00"


def test_categorize_sends_only_the_merchant():
    from engine.categorize.rules import _llm_cache, categorize

    _llm_cache.clear()
    sent = []
    categorize("BLINKIT", "UPI/412345007919/BLINKIT/blinkit@okaxis/Payment", [], lambda p: sent.append(p) or "Food")
    assert "BLINKIT" in sent[0] and "412345007919" not in sent[0] and "@okaxis" not in sent[0] and "Description" not in sent[0]


def test_pdf_fallback_sends_only_transaction_lines():
    text = "Customer: DEMO USER\n12 Main Street, Pune\nA/c 123456789012\n05/10/2026 SWIGGY 420.00 74,580.00\nPage 1 of 2"
    assert txn_lines(text) == "05/10/2026 SWIGGY 420.00 74,580.00"
    sent = []
    extract_with_llm(text, "pdf", lambda p: sent.append(p) or "[]")
    assert "DEMO USER" not in sent[0] and "Main Street" not in sent[0] and "123456789012" not in sent[0]

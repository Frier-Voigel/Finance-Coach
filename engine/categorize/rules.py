"""Rule-based transaction categorisation engine with LLM fallback."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Callable

from shared.schema import Rule

DEFAULT_CATEGORIES = [
    "Food", "Transport", "Shopping", "Entertainment",
    "Utilities", "Rent", "Salary", "Subscriptions", "Health", "Other",
]

# Well-known merchant → category defaults (applied after DB rules, before LLM)
MERCHANT_DEFAULTS: dict[str, str] = {
    "SWIGGY": "Food",
    "ZOMATO": "Food",
    "NETFLIX": "Subscriptions",
    "SPOTIFY": "Subscriptions",
    "GYMFIT": "Health",
    "UBER INDIA": "Transport",
    "BIGBASKET": "Food",
    "DMART": "Shopping",
    "AMAZON PAY INDIA": "Shopping",
    "MYNTRA": "Shopping",
    "JIO PREPAID": "Utilities",
    "BSES RAJDHANI": "Utilities",
    "CAFE COFFEE DAY": "Food",
    "LANDLORD RAJESH": "Rent",
    "ACME TECHNOLOGIES": "Salary",
}

# Module-level LLM cache: hash(merchant+description) -> category
_llm_cache: dict[str, str] = {}


def _match_merchant(rule: Rule, merchant: str) -> bool:
    """Exact case-insensitive match on the merchant field."""
    return rule.pattern.upper() == merchant.upper()


def _match_contains(rule: Rule, description: str) -> bool:
    """Case-insensitive substring match on the description."""
    return rule.pattern.upper() in description.upper()


def _match_regex(rule: Rule, description: str) -> bool:
    """Regex match against the description (case-insensitive)."""
    try:
        return bool(re.search(rule.pattern, description, re.IGNORECASE))
    except re.error:
        return False


def apply_rules(merchant: str, description: str, db_rules: list[Rule]) -> str | None:
    """Try DB rules in priority order: merchant > contains > regex.

    Returns the matched category or ``None`` if no rule matches.
    """
    merchant_rules = [r for r in db_rules if r.match_type == "merchant"]
    contains_rules = [r for r in db_rules if r.match_type == "contains"]
    regex_rules = [r for r in db_rules if r.match_type == "regex"]

    for rule in merchant_rules:
        if _match_merchant(rule, merchant):
            return rule.category

    for rule in contains_rules:
        if _match_contains(rule, description):
            return rule.category

    for rule in regex_rules:
        if _match_regex(rule, description):
            return rule.category

    return None


def _llm_categorize(merchant: str, description: str, llm: Callable[[str], str]) -> str:
    """Ask the LLM to classify the transaction; cache by input hash."""
    cache_key = hashlib.sha256(f"{merchant}||{description}".encode()).hexdigest()
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    categories_str = ", ".join(DEFAULT_CATEGORIES)
    prompt = (
        f"Classify this bank transaction into exactly one category.\n"
        f"Categories: {categories_str}\n"
        f"Merchant: {merchant}\n"
        f"Description: {description}\n"
        f"Reply with only the category name, nothing else."
    )
    raw = llm(prompt).strip()

    # Normalise: pick the closest known category, fall back to Other
    for cat in DEFAULT_CATEGORIES:
        if cat.lower() == raw.lower():
            _llm_cache[cache_key] = cat
            return cat

    # Try to extract a known category from the response
    for cat in DEFAULT_CATEGORIES:
        if cat.lower() in raw.lower():
            _llm_cache[cache_key] = cat
            return cat

    _llm_cache[cache_key] = "Other"
    return "Other"


def categorize(
    merchant: str,
    description: str,
    db_rules: list[Rule],
    llm: Callable[[str], str] | None = None,
) -> tuple[str, str]:
    """Return *(category, source)* for a transaction.

    Priority:
    1. DB rules (``apply_rules``) → source ``"rule"``
    2. ``MERCHANT_DEFAULTS`` → source ``"rule"``
    3. LLM fallback (if *llm* is provided) → source ``"llm"``
    4. ``"Other"`` → source ``"default"``
    """
    cat = apply_rules(merchant, description, db_rules)
    if cat:
        return cat, "rule"

    default = MERCHANT_DEFAULTS.get(merchant.upper())
    if default:
        return default, "rule"

    if llm:
        cat = _llm_categorize(merchant, description, llm)
        return cat, "llm"

    return "Other", "default"

"""No specific securities (Person B). Rule-based; add an LLM classifier on top later, never instead."""
from __future__ import annotations

import re
from typing import Callable

REDIRECT = (
    "I can't recommend specific stocks, funds or crypto. What I can do is model how much you can invest "
    "from your monthly surplus, show how that affects your goals, and explain in general how different "
    "kinds of investments work. For picks, a SEBI-registered advisor is the right person. "
    "Educational modelling only, not financial advice."
)

_ASSETS = (
    r"bitcoin|btc|ethereum|ether|dogecoin|solana|xrp|tesla|nvidia|reliance|tcs|infosys|nifty ?bees|bluechip fund"
)
_KINDS = r"stocks?|shares?|mutual funds?|funds?|etfs?|crypto(?:currenc(?:y|ies))?|coins?|schemes?|securit(?:y|ies)"

_ASK = [
    rf"\b(which|what|best|top|good)\b.*\b({_KINDS})\b",
    rf"\bshould i (buy|sell|invest in|put money in|hold|short)\b.*\b({_KINDS}|{_ASSETS})\b",
    r"\bshould i (buy|sell|invest in|hold|short) \$[a-z]{1,5}\b",
    r"\bis\b.*\b(a good (buy|investment)|worth (buying|investing)|going (up|to (rise|crash)))\b",
    rf"\b({_ASSETS})\b.*\b(buy|sell|invest|good|worth|predict|price target)\b",
    rf"\b(buy|sell|invest in)\b.*\b({_ASSETS})\b",
]
_EDU = re.compile(r"^\s*(what is|what are|what's|how do|how does|explain|difference between)\b")
_PICKY = re.compile(r"\b(should i|which|best|top|buy|sell)\b")

_OUT = [
    r"\$[A-Za-z]{1,5}\b",
    rf"\b(buy|sell|invest in|put your money in|go for)\s+({_ASSETS})\b",
    rf"\b(i|we) (recommend|suggest)\b.*\b({_ASSETS}|{_KINDS})\b",
]


def asks_for_security_advice(text: str) -> bool:
    low = text.lower()
    if _EDU.match(low) and not _PICKY.search(low):
        return False  # general education is allowed
    return any(re.search(p, low) for p in _ASK)


def output_violates(text: str) -> bool:
    """Check coach/LLM output before it reaches the user."""
    return any(re.search(p, text, re.I) for p in _OUT)


def guard(user_text: str, answer: str | None = None, classifier: Callable[[str], bool] | None = None) -> str | None:
    """Return the redirect if the request or the draft answer breaks the rule, else None.

    The rules always run first. `classifier` (an LLM yes/no check) is an extra layer on top: it can only add a block,
    and if it fails the rule-based verdict stands.
    """
    if asks_for_security_advice(user_text) or (answer and output_violates(answer)):
        return REDIRECT
    if classifier:
        try:
            if classifier(user_text):
                return REDIRECT
        except Exception:  # noqa: BLE001 - a flaky LLM must never break the request path
            pass
    return None

"""Thin Gemini Flash wrapper for Person B (free tier). Swap for /shared/llm.py once Person A's wrapper lands.

Every function returns None / False when no key is set or the call fails, so callers fall back to rules.
"""
from __future__ import annotations

import logging
import os
from typing import Callable

log = logging.getLogger(__name__)


def generate(prompt: str) -> str | None:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=key)
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
        return model.generate_content(prompt).text
    except Exception as e:  # noqa: BLE001 - free tier rate limits etc. must not crash the app
        log.warning("Gemini call failed: %s", e)
        return None


def llm_or_none() -> Callable[[str], str | None] | None:
    return generate if os.getenv("GEMINI_API_KEY") else None


def classify_security_advice(text: str) -> bool:
    """LLM yes/no: is the user asking which specific security to buy, sell or hold?"""
    out = generate(
        "Answer only YES or NO. Is this message asking which specific named stock, fund, ETF, crypto or other "
        "security to buy, sell or hold (not general education, not budgeting)?\n\nMessage: " + text
    )
    return bool(out) and out.strip().upper().startswith("YES")

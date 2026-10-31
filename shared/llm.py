"""Thin wrapper around Gemini Flash for text completion with module-level caching."""
from __future__ import annotations

import hashlib
import os
from typing import TYPE_CHECKING

# Module-level cache: sha256(prompt) -> response str
_cache: dict[str, str] = {}


def complete(prompt: str) -> str:
    """Send *prompt* to Gemini Flash and return the text response.

    Results are cached in memory (hash → response) to avoid redundant API calls.
    Reads ``GEMINI_API_KEY`` from the environment.

    Raises
    ------
    ImportError
        If ``google-generativeai`` is not installed.
    RuntimeError
        If ``GEMINI_API_KEY`` is missing.
    """
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "google-generativeai is not installed. "
            "Run: pip install google-generativeai"
        ) from exc

    key = hashlib.sha256(prompt.encode()).hexdigest()
    if key in _cache:
        return _cache[key]

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable is not set. "
            "Add it to your .env file or export it before running."
        )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    text: str = response.text.strip()
    _cache[key] = text
    return text

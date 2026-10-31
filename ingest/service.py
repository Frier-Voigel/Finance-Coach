"""Ingest orchestration: pick a parser by file type, fall back to the LLM, dedupe."""
from __future__ import annotations

from dataclasses import dataclass, field

from ingest.csv_parser import parse_csv
from ingest.llm_fallback import LLM, extract_with_llm
from ingest.models import ParsedTxn
from ingest.normalizer import dedupe
from ingest.pdf_parser import parse_pdf
from ingest.sms_parser import parse_sms_batch


class UnsupportedFile(ValueError):
    """Raised for file types we cannot ingest."""


@dataclass
class IngestResult:
    transactions: list[ParsedTxn] = field(default_factory=list)
    duplicates_skipped: int = 0
    unparsed: list[str] = field(default_factory=list)


def ingest_file(filename: str, content: bytes, account: str = "", llm: LLM | None = None,
                existing_keys: set[tuple] | None = None) -> IngestResult:
    """Parse an uploaded statement (.csv or .pdf)."""
    name = filename.lower()
    unparsed: list[str] = []
    if name.endswith(".csv"):
        txns = parse_csv(content, account)
    elif name.endswith(".pdf"):
        txns, text = parse_pdf(content, account)
        if not txns and text.strip():
            if llm:
                txns = extract_with_llm(text, "pdf", llm, account=account)
            if not txns:
                unparsed = [text.strip()[:500]]
    else:
        raise UnsupportedFile(f"unsupported file type: {filename}")
    return _finish(txns, unparsed, existing_keys)


def ingest_sms(blob: str, default_year: int | None = None, llm: LLM | None = None,
               existing_keys: set[tuple] | None = None) -> IngestResult:
    """Parse pasted SMS text; unmatched messages go to the LLM fallback if provided."""
    txns, unmatched = parse_sms_batch(blob, default_year)
    if unmatched and llm:
        extra = extract_with_llm("\n".join(unmatched), "sms", llm, default_year)
        if extra:
            txns, unmatched = txns + extra, []
    return _finish(txns, unmatched, existing_keys)


def _finish(txns: list[ParsedTxn], unparsed: list[str], existing: set[tuple] | None) -> IngestResult:
    kept = dedupe(txns, existing)
    return IngestResult(kept, len(txns) - len(kept), unparsed)

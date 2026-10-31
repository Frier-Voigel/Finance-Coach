"""PDF statement parser: pdfplumber tables first; page text is returned for the LLM fallback."""
from __future__ import annotations

import io

from ingest.csv_parser import parse_rows
from ingest.models import ParsedTxn


def parse_tables(tables: list[list[list[str | None]]], account: str = "") -> list[ParsedTxn]:
    """Parse extracted tables (rows of cells). Tables without a usable header are skipped."""
    out: list[ParsedTxn] = []
    for table in tables:
        rows = [[(c or "").replace("\n", " ").strip() for c in row] for row in table]
        try:
            out.extend(parse_rows(rows, "pdf", account))
        except ValueError:
            continue
    return out


def parse_pdf(content: bytes, account: str = "") -> tuple[list[ParsedTxn], str]:
    """Return (transactions, page_text). Empty transactions means use the LLM fallback on page_text."""
    import pdfplumber  # imported lazily so the rest of ingest works without it

    tables: list[list[list[str | None]]] = []
    texts: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            tables.extend(page.extract_tables())
            texts.append(page.extract_text() or "")
    return parse_tables(tables, account), "\n".join(texts)

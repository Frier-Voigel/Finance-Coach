"""FastAPI router for POST /ingest/upload and POST /ingest/sms (owner: Person A)."""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ingest.llm_fallback import LLM
from ingest.models import ParsedTxn
from ingest.normalizer import keys_for
from ingest.service import IngestResult, UnsupportedFile, ingest_file, ingest_sms

log = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])


class InMemoryRepository:
    """Placeholder store until /shared/schema.py is frozen; swap for the SQLModel-backed one."""

    def __init__(self) -> None:
        self.rows: list[ParsedTxn] = []

    def existing_keys(self) -> set[tuple]:
        return keys_for(self.rows)

    def save(self, txns: list[ParsedTxn]) -> None:
        self.rows.extend(txns)


repository = InMemoryRepository()


def _get_llm() -> LLM | None:
    """Return the shared Gemini wrapper if /shared/llm.py exists, else None (rules only)."""
    try:
        from shared.llm import complete  # type: ignore
    except ImportError:
        return None
    return complete


class SmsRequest(BaseModel):
    messages: str
    default_year: int | None = None


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "message": message})


def _existing_keys() -> set[tuple]:
    keys = set(repository.existing_keys())
    try:
        from shared.db import get_engine
        from shared.schema import Transaction
        from sqlmodel import Session, select
        with Session(get_engine()) as session:
            keys |= keys_for(session.exec(select(Transaction).order_by(Transaction.id)).all())
    except Exception:
        pass
    return keys


def _respond(result: IngestResult):
    """Save to the database FIRST; only remember rows in memory once the save worked.

    Previously the rows went into the in-memory list before the DB save and any DB error was
    swallowed, so a failed save looked like success and the next upload said "duplicate".
    """
    try:
        from shared.db import get_engine
        from engine.categorize.service import save_parsed_txns
        from sqlmodel import Session
    except ImportError:  # DB layer not installed: rules-only, in-memory mode
        repository.save(result.transactions)
        return {
            "inserted": len(result.transactions),
            "duplicates_skipped": result.duplicates_skipped,
            "unparsed": result.unparsed,
            "transactions": [
                {"date": t.date.isoformat(), "amount": str(t.amount), "direction": t.direction,
                 "description": t.description, "merchant": t.merchant, "source": t.source,
                 "account": t.account}
                for t in result.transactions
            ],
        }

    try:
        with Session(get_engine()) as session:
            saved = save_parsed_txns(result.transactions, session, _get_llm())
            payload = {
                "inserted": len(saved),
                "duplicates_skipped": result.duplicates_skipped,
                "unparsed": result.unparsed,
                "transactions": [
                    {
                        "id": t.id,
                        "date": t.date.isoformat(),
                        "amount": str(t.amount),
                        "direction": t.direction,
                        "description": t.description,
                        "merchant": t.merchant,
                        "category": t.category,
                        "category_source": t.category_source,
                        "source": t.source,
                        "account": t.account,
                    }
                    for t in saved
                ],
            }
    except Exception as exc:  # surface the real error instead of hiding it
        log.exception("ingest: saving transactions to the database failed")
        return _error(500, "db_save_failed", f"Could not save transactions: {exc}")
    repository.save(result.transactions)
    return payload


@router.post("/upload")
async def upload(file: UploadFile = File(...), account: str = Form("")):
    """Ingest a CSV or PDF statement."""
    content = await file.read()
    try:
        result = ingest_file(file.filename or "", content, account, _get_llm(),
                             _existing_keys())
    except UnsupportedFile as exc:
        return _error(415, "unsupported_file", str(exc))
    except ValueError as exc:
        return _error(422, "parse_failed", str(exc))
    return _respond(result)


@router.post("/sms")
def sms(body: SmsRequest):
    """Ingest pasted SMS alerts (one per line)."""
    if not body.messages.strip():
        return _error(422, "empty_input", "Paste at least one SMS.")
    return _respond(ingest_sms(body.messages, body.default_year, _get_llm(),
                               _existing_keys()))

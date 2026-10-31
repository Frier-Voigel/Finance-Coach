"""Skeleton router for Person A data ingestion (CSV, SMS, PDF)."""
from __future__ import annotations

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

router = APIRouter(prefix="/ingest", tags=["ingest"])


class SmsIngestReq(BaseModel):
    text: str | None = None
    messages: list[str] | None = None


@router.post("/upload")
async def upload_statement(file: UploadFile = File(...)):
    """Upload bank statement (CSV or PDF). Person A implementation stub."""
    return {
        "filename": file.filename,
        "parsed": 0,
        "inserted": 0,
        "transactions": [],
        "message": "Ingest skeleton: parser will be implemented in Phase A1.",
    }


@router.post("/sms")
def ingest_sms(body: SmsIngestReq):
    """Ingest SMS transaction text. Person A implementation stub."""
    return {
        "parsed": 0,
        "inserted": 0,
        "transactions": [],
        "message": "Ingest skeleton: SMS parser will be implemented in Phase A1.",
    }

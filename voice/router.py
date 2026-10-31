"""B4 endpoints: /voice/token, /voice/command, /voice/confirm."""
from __future__ import annotations

import urllib.error
import uuid
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.deps import get_store, get_today
from api.errors import ApiError
from coach.gemini import classify_security_advice, llm_or_none
from voice import service
from voice.llm_intent import make_llm_parser
from voice.wispr import WisprNotConfigured, get_client_token

router = APIRouter(tags=["voice"])


class TokenRequest(BaseModel):
    client_id: str | None = None


class CommandRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class ConfirmRequest(BaseModel):
    log_id: int
    accept: bool = True


@router.post("/voice/token")
def voice_token(body: TokenRequest | None = None) -> dict:
    """Short-lived Wispr token for the browser. The org API key never leaves the backend."""
    try:
        return get_client_token(client_id=(body and body.client_id) or uuid.uuid4().hex, duration_secs=600)
    except WisprNotConfigured as e:
        raise ApiError(503, "wispr_not_configured", "Voice is not set up on the server. Type your command instead.") from e
    except (urllib.error.URLError, KeyError, ValueError) as e:
        raise ApiError(502, "wispr_unavailable", "Could not get a voice token from Wispr Flow. Type your command instead.") from e


@router.post("/voice/command")
def voice_command(body: CommandRequest, store=Depends(get_store), today: date = Depends(get_today)) -> dict:
    """Transcript or typed text -> confirmation cards. Writes nothing; call /voice/confirm to apply."""
    generate = llm_or_none()
    return service.handle_command(store, body.text, today, llm=make_llm_parser(generate) if generate else None,
                                  classifier=classify_security_advice if generate else None)


@router.post("/voice/confirm")
def voice_confirm(body: ConfirmRequest, store=Depends(get_store), today: date = Depends(get_today)) -> dict:
    try:
        out = service.confirm(store, body.log_id, body.accept, today)
    except ValueError as e:
        raise ApiError(409, "already_resolved", str(e)) from e
    if out is None:
        raise ApiError(404, "log_not_found", f"No voice command with id {body.log_id}.")
    return out

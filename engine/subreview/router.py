"""Subscription review endpoints: GET /subscriptions/review, POST /subscriptions/review/{merchant_hash}/answer."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from api.deps import get_today
from api.errors import ApiError
from engine.subreview import service
from shared.db import get_session

router = APIRouter(tags=["subscription-review"])


class AnswerIn(BaseModel):
    answer: Literal["using", "not_using"]


@router.get("/subscriptions/review")
def read_review(session: Session = Depends(get_session), today: date = Depends(get_today)) -> dict:
    return service.review(session, today)


@router.post("/subscriptions/review/{merchant_hash}/answer")
def answer(merchant_hash: str, body: AnswerIn, session: Session = Depends(get_session), today: date = Depends(get_today)) -> dict:
    try:
        merchant = service.answer(session, merchant_hash, body.answer)
    except KeyError as e:
        raise ApiError(404, "recurring_not_found", "No subscription with that id.") from e
    return {"merchant": merchant, "answer": body.answer, "review": service.review(session, today)}

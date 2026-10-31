"""B5 endpoint: POST /coach/ask."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.deps import get_store, get_today
from coach.explain import phrase, status_text, with_footer
from coach.gemini import classify_security_advice, llm_or_none
from coach.guardrails import guard
from engine.nudges.service import sync_nudges
from engine.planner.service import overview

router = APIRouter(tags=["coach"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@router.post("/coach/ask")
def ask(body: AskRequest, store=Depends(get_store), today: date = Depends(get_today)) -> dict:
    """Guardrail first; otherwise explain the user's plan in plain language. Always carries the footer."""
    llm = llm_or_none()
    redirect = guard(body.question, classifier=classify_security_advice if llm else None)
    if redirect:
        return {"answer": redirect, "blocked": True}
    facts = status_text(overview(store, today), sync_nudges(store, today))
    answer = phrase(facts, body.question, llm)
    return {"answer": with_footer(guard("", answer) or answer), "blocked": False}

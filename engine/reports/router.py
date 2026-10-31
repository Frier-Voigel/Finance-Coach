"""B3 endpoint: GET /reports/{month}?format=json|html."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from api.deps import get_store, get_today
from api.errors import ApiError
from engine.reports import service
from engine.reports.report import render_page

router = APIRouter(tags=["reports"])


@router.get("/reports/{month}", response_model=None)
def read_report(month: str, format: Literal["json", "html"] = "json", store=Depends(get_store),
                today: date = Depends(get_today)):
    try:
        report = service.build_report(store, month, today)
    except ValueError as e:
        raise ApiError(422, "bad_month", str(e)) from e
    return HTMLResponse(render_page(report)) if format == "html" else report

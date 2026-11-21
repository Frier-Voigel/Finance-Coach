"""Records 'what changed' around every request that can move the money model.

It snapshots the plan BEFORE the request, lets the request run untouched, snapshots AFTER, and stores the diff.
Observer only: any failure here is logged and swallowed, and the response is never altered. No router or
service of Person A or B had to change.
"""
from __future__ import annotations

import logging
import re
from contextlib import contextmanager

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool

from engine.changes import service
from shared.db import get_session

log = logging.getLogger(__name__)

TRIGGERS: list[tuple[str, re.Pattern, str]] = [
    ("POST", re.compile(r"^/ingest/upload$"), "upload"),
    ("POST", re.compile(r"^/ingest/sms$"), "sms"),
    ("PATCH", re.compile(r"^/transactions/\d+$"), "correction"),
    ("POST", re.compile(r"^/voice/confirm$"), "voice"),
    ("PUT", re.compile(r"^/profile$"), "profile"),
    ("POST", re.compile(r"^/goals$"), "goal"),
    ("PATCH", re.compile(r"^/goals/\d+$"), "goal"),
    ("POST", re.compile(r"^/recurring/[^/]+/mark-unused$"), "subscription"),
]


def classify(method: str, path: str) -> str | None:
    return next((t for m, rx, t in TRIGGERS if m == method and rx.match(path)), None)


@contextmanager
def _session(app: FastAPI):
    """Same session factory the routers use, so tests that override get_session are respected."""
    gen = app.dependency_overrides.get(get_session, get_session)()
    session = next(gen)
    try:
        yield session
    finally:
        gen.close()


def _snapshot(app: FastAPI, today):
    try:
        with _session(app) as s:
            return service.current_snapshot(s, today)
    except Exception:  # noqa: BLE001 - never break the request
        log.exception("what-changed: before-snapshot failed")
        return None


def _record(app: FastAPI, trigger: str, before: dict, today) -> None:
    try:
        with _session(app) as s:
            service.record_change(s, trigger, before, service.current_snapshot(s, today))
    except Exception:  # noqa: BLE001
        log.exception("what-changed: recording failed")


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def what_changed(request: Request, call_next):
        trigger = classify(request.method, request.url.path)
        if trigger is None:
            return await call_next(request)
        today = service.resolve_today(request.query_params.get("as_of"))
        before = await run_in_threadpool(_snapshot, app, today)
        response = await call_next(request)
        if before is not None and response.status_code < 400:
            await run_in_threadpool(_record, app, trigger, before, today)
        return response

"""FastAPI app. Both Person A and Person B routers mounted."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db import init_db
from api.errors import install_error_handlers
from coach.router import router as coach_router
from engine.categorize.router import router as categorize_router
from engine.nudges.router import router as nudges_router
from engine.planner.router import router as planner_router
from engine.recurring.router import router as recurring_router
from engine.reports.router import router as reports_router
from ingest.router import router as ingest_router
from voice.router import router as voice_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Finance Coach", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)
install_error_handlers(app)

# Person A routers
for r in (ingest_router, categorize_router, recurring_router):
    app.include_router(r)

# Person B routers
for r in (planner_router, nudges_router, reports_router, voice_router, coach_router):
    app.include_router(r)

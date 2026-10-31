"""FastAPI application entry-point (unified for Person A & Person B)."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env before importing anything that reads env vars
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from shared.db import init_db
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
    """Initialise database tables on application startup."""
    init_db()
    yield


app = FastAPI(title="Finance Coach API", version="0.1.0", lifespan=lifespan)

# CORS setup
cors_origin = os.getenv("CORS_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[cors_origin, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_error_handlers(app)

# ---------------------------------------------------------------------------
# Person A Routers (Ingestion, Categorisation, Recurring Detection)
# ---------------------------------------------------------------------------
app.include_router(ingest_router)          # POST /ingest/upload, POST /ingest/sms
app.include_router(categorize_router)      # GET /transactions, PATCH /transactions/{id}, GET/DELETE /rules
app.include_router(recurring_router)       # GET /recurring, POST /recurring/{merchant_hash}/mark-unused

# ---------------------------------------------------------------------------
# Person B Routers (Planner, What-if, Nudges, Reports, Voice, Coach)
# ---------------------------------------------------------------------------
for r in (planner_router, nudges_router, reports_router, voice_router, coach_router):
    app.include_router(r)


# ---------------------------------------------------------------------------
# Health / Liveness
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    """Liveness probe."""
    return {"status": "ok"}

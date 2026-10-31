"""Database engine and session dependency (re-exported from shared.db)."""
from __future__ import annotations

from shared.db import engine, get_engine, get_session, init_db

__all__ = ["engine", "get_engine", "get_session", "init_db"]

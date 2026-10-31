"""SQLModel tables from SPEC section 7.

FROZEN: Shared database schema agreed upon by Person A and Person B.
Money is whole rupees (int). Dates are ISO in the DB.
"""
from __future__ import annotations

import datetime as dt

from sqlmodel import Field, SQLModel


def utcnow() -> dt.datetime:
    """Naive UTC timestamp (datetime.utcnow() is deprecated)."""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    id: int | None = Field(default=None, primary_key=True)
    date: dt.date
    amount: int
    direction: str  # debit | credit
    description: str
    merchant: str | None = None
    category: str | None = None
    category_source: str | None = None  # rule | llm | user
    source: str = "csv"  # csv | pdf | sms | voice
    raw_text: str | None = None
    account: str | None = None


class Rule(SQLModel, table=True):
    __tablename__ = "rules"
    id: int | None = Field(default=None, primary_key=True)
    pattern: str
    match_type: str = "contains"  # contains | regex | merchant
    category: str
    created_from_txn_id: int | None = None
    created_at: dt.datetime = Field(default_factory=utcnow)


class Recurring(SQLModel, table=True):
    __tablename__ = "recurring"
    id: int | None = Field(default=None, primary_key=True)
    merchant: str
    amount: int
    cadence: str  # weekly | monthly | yearly
    last_seen: dt.date | None = None
    next_expected: dt.date | None = None
    status: str = "active"  # active | changed | unused | cancelled


class Profile(SQLModel, table=True):
    __tablename__ = "profile"
    id: int | None = Field(default=None, primary_key=True)
    monthly_income: int = 0
    fixed_costs_json: str = "{}"
    emergency_fund_current: int = 0
    emergency_fund_target: int = 0
    updated_at: dt.datetime = Field(default_factory=utcnow)


class Goal(SQLModel, table=True):
    __tablename__ = "goals"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    target_amount: int
    current_amount: int = 0
    target_date: dt.date | None = None
    priority: int = 1


class Nudge(SQLModel, table=True):
    __tablename__ = "nudges"
    id: int | None = Field(default=None, primary_key=True)
    created_at: dt.datetime = Field(default_factory=utcnow)
    type: str
    message: str
    severity: str = "medium"
    dismissed: bool = False


class Report(SQLModel, table=True):
    __tablename__ = "reports"
    id: int | None = Field(default=None, primary_key=True)
    month: str  # YYYY-MM
    json_payload: str
    generated_at: dt.datetime = Field(default_factory=utcnow)


class VoiceLog(SQLModel, table=True):
    __tablename__ = "voice_log"
    id: int | None = Field(default=None, primary_key=True)
    created_at: dt.datetime = Field(default_factory=utcnow)
    transcript: str
    intent_json: str
    confirmed: bool = False
    result: str | None = None  # NULL = still waiting for the user's confirmation

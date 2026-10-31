"""SQLModel table definitions shared across all modules (unified for Person A & B)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)



class Transaction(SQLModel, table=True):
    """One financial transaction row."""

    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: date
    amount: Decimal = Field(default=Decimal("0"))
    direction: str  # "debit" | "credit"
    description: str
    merchant: str = ""
    category: str = "Other"
    category_source: Optional[str] = "rule"  # "rule" | "llm" | "user"
    source: str = "csv"  # "csv" | "pdf" | "sms" | "voice"
    raw_text: Optional[str] = ""
    account: Optional[str] = ""


class Rule(SQLModel, table=True):
    """Categorisation rule, created manually or via correction loop."""

    __tablename__ = "rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    pattern: str
    match_type: str = "contains"  # "contains" | "regex" | "merchant"
    category: str
    created_from_txn_id: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)


class Recurring(SQLModel, table=True):
    """Detected or user-annotated recurring charge."""

    __tablename__ = "recurring"

    id: Optional[int] = Field(default=None, primary_key=True)
    merchant: str = Field(index=True)
    amount: Decimal = Field(default=Decimal("0"))
    cadence: str = "monthly"  # "weekly" | "monthly" | "yearly"
    last_seen: Optional[date] = None
    next_expected: Optional[date] = None
    status: str = "active"  # "active" | "changed" | "unused" | "cancelled"


class Profile(SQLModel, table=True):
    """User financial profile (singleton row, id=1)."""

    __tablename__ = "profile"

    id: Optional[int] = Field(default=None, primary_key=True)
    monthly_income: Decimal = Field(default=Decimal("0"))
    fixed_costs_json: str = "{}"
    emergency_fund_current: Decimal = Field(default=Decimal("0"))
    emergency_fund_target: Decimal = Field(default=Decimal("0"))
    updated_at: datetime = Field(default_factory=utcnow)


class Goal(SQLModel, table=True):
    """A savings or spending goal."""

    __tablename__ = "goals"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    target_amount: Decimal = Field(default=Decimal("0"))
    current_amount: Decimal = Field(default=Decimal("0"))
    target_date: Optional[date] = None
    priority: int = 1


class Nudge(SQLModel, table=True):
    """An actionable insight or alert shown to the user."""

    __tablename__ = "nudges"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    type: str
    message: str
    severity: str = "medium"  # "high" | "medium" | "low" | "info" | "warning"
    dismissed: bool = False


class Report(SQLModel, table=True):
    """Cached monthly report payload."""

    __tablename__ = "reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    month: str  # "YYYY-MM"
    json_payload: str
    generated_at: datetime = Field(default_factory=utcnow)


class VoiceLog(SQLModel, table=True):
    """Voice command transcript and resolved intent."""

    __tablename__ = "voice_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    transcript: str
    intent_json: str = "[]"
    confirmed: bool = False
    result: Optional[str] = None

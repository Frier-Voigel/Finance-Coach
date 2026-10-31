"""Request bodies for the planner endpoints (pydantic only, no web framework imports)."""
from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Rupees = int  # whole rupees


class ProfileIn(BaseModel):
    monthly_income: int = Field(ge=0)
    fixed_costs: dict[str, int] = Field(default_factory=dict)
    emergency_fund_current: int = Field(default=0, ge=0)
    emergency_fund_target: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _non_negative_costs(self):
        if any(v < 0 for v in self.fixed_costs.values()):
            raise ValueError("fixed_costs values must be >= 0")
        return self


class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: int = Field(gt=0)
    current_amount: int = Field(default=0, ge=0)
    target_date: dt.date | None = None
    priority: int | None = Field(default=None, ge=0)


class GoalPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: int | None = Field(default=None, gt=0)
    current_amount: int | None = Field(default=None, ge=0)
    target_date: dt.date | None = None
    priority: int | None = Field(default=None, ge=0)


class WhatIfRequest(BaseModel):
    kind: Literal["category_pct", "category_abs", "fixed_abs", "income_abs"]
    category: str | None = None
    name: str | None = None
    pct: float | None = Field(default=None, ge=-100)
    delta: int | None = None

    @model_validator(mode="after")
    def _required_fields(self):
        need = {"category_pct": ("category", "pct"), "category_abs": ("category", "delta"),
                "fixed_abs": ("name", "delta"), "income_abs": ("delta",)}[self.kind]
        missing = [f for f in need if getattr(self, f) is None]
        if missing:
            raise ValueError(f"{self.kind} needs: {', '.join(missing)}")
        return self

    def change(self) -> dict:
        """The plain dict the planner expects."""
        return self.model_dump(exclude_none=True)

"""Pydantic payloads for /credit."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class OverrideIn(BaseModel):
    customer_id: int
    credit_limit: Decimal
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("credit_limit", mode="before")
    @classmethod
    def _v(cls, v: object) -> object:
        if isinstance(v, float):
            raise ValueError("float is forbidden for money; use string or Decimal")
        return v


class PaymentIn(BaseModel):
    paid_on: date


class FreezeIn(BaseModel):
    reason: str = Field(min_length=5, max_length=500)

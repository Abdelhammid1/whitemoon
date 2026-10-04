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


class CollectPaymentIn(BaseModel):
    customer_id: int
    due_id: int | None = None
    amount: Decimal = Field(gt=0)
    paid_on: date

    @field_validator("amount", mode="before")
    @classmethod
    def _no_float_amt(cls, v: object) -> object:
        if isinstance(v, float):
            raise ValueError("float is forbidden for money; use string or Decimal")
        return v


class RejectPaymentIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class TierSettingIn(BaseModel):
    credit_limit: Decimal = Field(ge=0)
    deferred_pct: Decimal = Field(ge=0, le=100)

    @field_validator("credit_limit", "deferred_pct", mode="before")
    @classmethod
    def _no_float(cls, v: object) -> object:
        if isinstance(v, float):
            raise ValueError("float is forbidden for money; use string or Decimal")
        return v

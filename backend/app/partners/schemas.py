"""Request bodies for the /partners blueprint (EPIC 6)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class CreatePartnerIn(BaseModel):
    type: str = Field(pattern="^(agent|branch)$")
    display_name: str = Field(min_length=1, max_length=200)
    geo_scope: str | None = Field(default=None, max_length=200)
    phone: str | None = None
    email: str | None = None
    password: str = Field(min_length=8, max_length=128)
    # Terms (agents only; ignored/zeroed for a branch).
    earns_commission: bool = False
    commission_rate_pct: float = Field(default=0, ge=0, le=100)
    earns_investment_return: bool = False
    investment_return_rate_pct: float = Field(default=0, ge=0, le=100)


class TermsIn(BaseModel):
    earns_commission: bool = False
    commission_rate_pct: float = Field(default=0, ge=0, le=100)
    earns_investment_return: bool = False
    investment_return_rate_pct: float = Field(default=0, ge=0, le=100)


class DepositIn(BaseModel):
    amount: float = Field(gt=0)
    deposit_date: date
    recovery_conditions: str = Field(min_length=5, max_length=2000)


class RefundIn(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class AccrualIn(BaseModel):
    kind: str = Field(pattern="^(commission|investment_return)$")
    year: int = Field(ge=2020, le=2100)
    month: int = Field(ge=1, le=12)


class AttributeIn(BaseModel):
    partner_id: int = Field(gt=0)

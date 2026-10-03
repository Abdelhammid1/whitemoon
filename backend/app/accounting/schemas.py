"""Pydantic payloads for the /accounting endpoints."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ManualJournalLineIn(BaseModel):
    account_code: str = Field(min_length=1, max_length=10)
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    partner_type: str | None = None
    partner_id: int | None = None
    description: str | None = None

    @field_validator("debit", "credit", mode="before")
    @classmethod
    def _reject_float(cls, v: object) -> object:
        if isinstance(v, float):
            raise ValueError("float is forbidden for money; use string or Decimal")
        return v


class ManualJournalIn(BaseModel):
    entry_date: date
    description: str = Field(min_length=10, max_length=1000)
    reason: str = Field(min_length=10, max_length=1000)
    allow_closed_period: bool = False
    lines: list[ManualJournalLineIn] = Field(min_length=2)


class PeriodIn(BaseModel):
    year: int = Field(ge=2020, le=2100)
    month: int = Field(ge=1, le=12)


class ReceiptUploadIn(BaseModel):
    image_s3_key: str = Field(min_length=1, max_length=500)
    expected_amount: Decimal | None = None
    expected_reference: str | None = None
    # For the stub provider: the body may carry the OCR values directly so
    # tests can seed them without a real image.
    ocr_stub_amount: Decimal | None = None
    ocr_stub_reference: str | None = None


class ResolveReceiptIn(BaseModel):
    status: str = Field(pattern="^(matched|rejected)$")


class DeferredTermsIn(BaseModel):
    order_id: int
    cash_price: Decimal
    deferred_price: Decimal
    early_settlement_discount: Decimal = Decimal("0")
    early_settlement_before: date | None = None


class ApplyEarlyDiscountIn(BaseModel):
    order_id: int
    settled_on: date


class ReportFilterIn(BaseModel):
    date_from: date
    date_to: date
    account_prefix: str | None = None
    partner_type: str | None = None
    partner_id: int | None = None

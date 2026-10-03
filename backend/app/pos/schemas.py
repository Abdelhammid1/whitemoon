"""Request bodies for the /pos blueprint (EPIC 8)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SaleLine(BaseModel):
    product_id: int = Field(gt=0)
    supplier_id: int = Field(gt=0)
    qty: float = Field(gt=0)
    unit_price: float = Field(ge=0)


class CreateSaleIn(BaseModel):
    location_type: str = "channel_partner"
    location_id: int | None = None
    lines: list[SaleLine] = Field(min_length=1)


class SettleIn(BaseModel):
    entry_date: date | None = None

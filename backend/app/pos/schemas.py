"""Request bodies for the /pos blueprint (EPIC 8)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SaleLine(BaseModel):
    product_id: int = Field(gt=0)
    supplier_id: int = Field(gt=0)
    qty: float = Field(gt=0)
    # No unit_price: the price is taken from the supplier's active offer
    # server-side, never from the client.


class CreateSaleIn(BaseModel):
    # No location here: the sale draws from the authenticated cashier's own
    # channel-partner location, derived server-side (a client-supplied
    # location would let a cashier sell from another location's stock).
    lines: list[SaleLine] = Field(min_length=1)


class SettleIn(BaseModel):
    entry_date: date | None = None

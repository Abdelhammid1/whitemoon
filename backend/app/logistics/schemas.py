"""Request bodies for the /logistics blueprint (EPIC 9)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class CreateSlotIn(BaseModel):
    slot_date: date
    window: str = Field(min_length=1, max_length=40)
    capacity: int = Field(gt=0)


class BookSlotIn(BaseModel):
    order_id: int = Field(gt=0)
    slot_id: int = Field(gt=0)
    carrier_type: str = Field(default="internal", pattern="^(internal|external)$")


class StatusIn(BaseModel):
    status: str = Field(pattern="^(shipped|in_transit|failed)$")


class LocationIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class ShortageLine(BaseModel):
    product_id: int = Field(gt=0)
    qty: float = Field(gt=0)
    photo_url: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=1000)


class ConfirmDeliveryIn(BaseModel):
    confirmation_code: str | None = None
    signature: str | None = Field(default=None, max_length=2000)
    shortages: list[ShortageLine] = Field(default_factory=list)

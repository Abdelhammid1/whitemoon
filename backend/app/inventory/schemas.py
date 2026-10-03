"""Pydantic payloads for /inventory endpoints."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


def _reject_float(v: object) -> object:
    if isinstance(v, float):
        raise ValueError("float is forbidden for money/qty; use string or Decimal")
    return v


class ProductIn(BaseModel):
    sku: str = Field(min_length=1, max_length=60)
    name_ar: str = Field(min_length=1, max_length=200)
    name_en: str | None = None
    category: str = Field(pattern="^(food|clothing)$")
    unit: str = "piece"
    eta_code: str | None = None
    food_expiry_tracked: bool = False


class OfferIn(BaseModel):
    product_id: int
    unit_price: Decimal
    moq: Decimal = Decimal("0")
    is_active: bool = True

    @field_validator("unit_price", "moq", mode="before")
    @classmethod
    def _no_float(cls, v: object) -> object:
        return _reject_float(v)


class StockAdjustIn(BaseModel):
    supplier_id: int
    product_id: int
    location_type: str = Field(
        pattern="^(supplier|channel_partner|in_transit|customer_hold)$"
    )
    location_id: int | None = None
    delta: Decimal
    reorder_point: Decimal | None = None

    @field_validator("delta", "reorder_point", mode="before")
    @classmethod
    def _no_float(cls, v: object) -> object:
        return _reject_float(v)


class TransferLineIn(BaseModel):
    product_id: int
    qty: Decimal
    unit_cost: Decimal

    @field_validator("qty", "unit_cost", mode="before")
    @classmethod
    def _no_float(cls, v: object) -> object:
        return _reject_float(v)


class TransferOrderIn(BaseModel):
    supplier_id: int
    from_location_type: str = Field(
        pattern="^(supplier|channel_partner|in_transit|customer_hold)$"
    )
    from_location_id: int | None = None
    to_location_type: str = Field(
        pattern="^(supplier|channel_partner|in_transit|customer_hold)$"
    )
    to_location_id: int | None = None
    lines: list[TransferLineIn] = Field(min_length=1)


class ShortageIn(BaseModel):
    supplier_id: int
    product_id: int
    qty: Decimal
    unit_cost: Decimal
    transfer_order_id: int | None = None
    evidence_s3_keys: list[str] = Field(min_length=1)

    @field_validator("qty", "unit_cost", mode="before")
    @classmethod
    def _no_float(cls, v: object) -> object:
        return _reject_float(v)


class ShortageResolveIn(BaseModel):
    responsible_party_type: str = Field(
        pattern="^(supplier|channel_partner|unallocated)$"
    )
    responsible_party_id: int | None = None
    reason: str = Field(min_length=5, max_length=1000)

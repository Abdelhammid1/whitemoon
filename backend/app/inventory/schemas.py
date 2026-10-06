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
    # Validated against the live categories table in the service (T-15), not a
    # hardcoded list — admins can add categories.
    category: str = Field(min_length=1, max_length=40, pattern=r"^[a-z][a-z0-9_]*$")
    unit: str = "piece"
    eta_code: str | None = None
    food_expiry_tracked: bool = False
    subcategory: str | None = Field(default=None, max_length=120)
    brand: str | None = Field(default=None, max_length=120)
    barcode: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)


class VariantIn(BaseModel):
    sku: str = Field(min_length=1, max_length=60)
    barcode: str | None = Field(default=None, max_length=60)
    size: str | None = Field(default=None, max_length=60)
    color: str | None = Field(default=None, max_length=60)


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

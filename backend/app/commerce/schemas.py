"""Pydantic payloads for /catalog and /commerce."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


def _no_float(v: object) -> object:
    if isinstance(v, float):
        raise ValueError("float is forbidden for money/qty; use string or Decimal")
    return v


class AddCartItemIn(BaseModel):
    offer_id: int
    qty: Decimal

    @field_validator("qty", mode="before")
    @classmethod
    def _v(cls, v: object) -> object:
        return _no_float(v)


class UpdateCartItemIn(BaseModel):
    qty: Decimal

    @field_validator("qty", mode="before")
    @classmethod
    def _v(cls, v: object) -> object:
        return _no_float(v)


class CheckoutIn(BaseModel):
    # Financial terms (deferred price, discount, window) are computed
    # server-side from the approved schedule — never accepted from the client.
    payment_mode: str = Field(pattern="^(cash|deferred)$")


class RfqIn(BaseModel):
    product_id: int
    qty: Decimal
    deadline: date | None = None
    qualification_requirements: str | None = Field(default=None, max_length=1000)

    @field_validator("qty", mode="before")
    @classmethod
    def _v(cls, v: object) -> object:
        return _no_float(v)


class RfqOfferIn(BaseModel):
    unit_price: Decimal
    moq: Decimal = Decimal("0")

    @field_validator("unit_price", "moq", mode="before")
    @classmethod
    def _v(cls, v: object) -> object:
        return _no_float(v)

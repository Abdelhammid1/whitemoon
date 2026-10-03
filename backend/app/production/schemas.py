"""Request bodies for the /production blueprint (EPIC 7)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class MaterialLine(BaseModel):
    product_id: int = Field(gt=0)
    qty: float = Field(gt=0)
    unit_cost: float = Field(ge=0)


class CreateMOIn(BaseModel):
    owner_id: int = Field(gt=0)
    output_product_id: int = Field(gt=0)
    output_qty: float = Field(gt=0)
    materials: list[MaterialLine] = Field(min_length=1)
    stages: list[str] = Field(min_length=1)
    location_type: str = "supplier"
    location_id: int | None = None


class CompleteMOIn(BaseModel):
    entry_date: date | None = None

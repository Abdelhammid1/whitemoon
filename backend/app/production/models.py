"""Manufacturing orders, their stages, and their bill of materials — EPIC 7.

Schema `production`. Stock lives in the inventory schema; a completed order
moves it. `owner_id` is the manufacturing party and is used as the
`supplier_id` key into `inventory.stock_balances` (which keys stock by its
owner), with `location_type='supplier'` meaning the owner's own warehouse.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..common.base_model import Base, TimestampMixin

MO_STATUSES = ("draft", "in_progress", "completed", "cancelled")
STAGE_STATUSES = ("pending", "done")


class ManufacturingOrder(Base, TimestampMixin):
    __tablename__ = "manufacturing_orders"
    __table_args__ = (
        UniqueConstraint("number", name="uq_manufacturing_orders_number"),
        CheckConstraint("output_qty > 0", name="ck_mo_output_qty_positive"),
        CheckConstraint(
            "status in ('draft','in_progress','completed','cancelled')",
            name="ck_mo_status",
        ),
        CheckConstraint(
            "location_type in ('supplier','channel_partner','in_transit','customer_hold')",
            name="ck_mo_location_type",
        ),
        CheckConstraint("currency = 'EGP'", name="ck_mo_currency_egp"),
        Index("ix_mo_owner", "owner_id"),
        {"schema": "production"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    output_product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    output_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    location_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="supplier"
    )
    location_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    total_material_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    journal_entry_id: Mapped[int | None] = mapped_column(BigInteger)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    stages: Mapped[list[MOStage]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="MOStage.seq"
    )
    materials: Mapped[list[MOMaterial]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="MOMaterial.id"
    )


class MOStage(Base):
    """One predefined stage of a manufacturing order (US-7.1)."""

    __tablename__ = "mo_stages"
    __table_args__ = (
        UniqueConstraint("mo_id", "seq", name="uq_mo_stages_seq"),
        CheckConstraint("status in ('pending','done')", name="ck_mo_stages_status"),
        {"schema": "production"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    mo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("production.manufacturing_orders.id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="pending")
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    order: Mapped[ManufacturingOrder] = relationship(back_populates="stages")


class MOMaterial(Base):
    """A raw-material input consumed when the order completes (US-7.2)."""

    __tablename__ = "mo_materials"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_mo_materials_qty_positive"),
        CheckConstraint("unit_cost >= 0", name="ck_mo_materials_unit_cost_nonneg"),
        Index("ix_mo_materials_mo", "mo_id"),
        {"schema": "production"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    mo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("production.manufacturing_orders.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    order: Mapped[ManufacturingOrder] = relationship(back_populates="materials")

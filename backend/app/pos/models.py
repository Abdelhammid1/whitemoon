"""POS sales, their lines, and settlement batches — EPIC 8.

Schema `pos`. Stock lives in the inventory schema and is deducted at sale
time; the financial posting is deferred to a `PosBatch` settlement run so POS
accounting is batched, not real-time (US-8.2).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..common.base_model import Base, TimestampMixin


class PosBatch(Base):
    """One settlement run: the journal posting for a set of POS sales."""

    __tablename__ = "pos_batches"
    __table_args__ = (
        CheckConstraint("currency = 'EGP'", name="ck_pos_batches_currency_egp"),
        {"schema": "pos"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    posted_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sale_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    journal_entry_id: Mapped[int | None] = mapped_column(BigInteger)


class PosSale(Base, TimestampMixin):
    __tablename__ = "pos_sales"
    __table_args__ = (
        UniqueConstraint("number", name="uq_pos_sales_number"),
        CheckConstraint("total >= 0", name="ck_pos_sales_total_nonneg"),
        CheckConstraint("status in ('completed','voided')", name="ck_pos_sales_status"),
        CheckConstraint(
            "location_type in ('supplier','channel_partner','in_transit','customer_hold')",
            name="ck_pos_sales_location_type",
        ),
        CheckConstraint("currency = 'EGP'", name="ck_pos_sales_currency_egp"),
        Index("ix_pos_sales_posted", "posted", "status"),
        {"schema": "pos"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    cashier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    location_type: Mapped[str] = mapped_column(String(20), nullable=False)
    location_id: Mapped[int | None] = mapped_column(BigInteger)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="completed")
    posted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    batch_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("pos.pos_batches.id")
    )
    sold_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lines: Mapped[list[PosSaleLine]] = relationship(
        back_populates="sale", cascade="all, delete-orphan", order_by="PosSaleLine.id"
    )


class PosSaleLine(Base):
    """One line of a POS sale. `supplier_id` identifies the stock slot (the
    stock owner) the item is drawn from — POS shares the inventory table."""

    __tablename__ = "pos_sale_lines"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_pos_sale_lines_qty_positive"),
        CheckConstraint("unit_price >= 0", name="ck_pos_sale_lines_unit_price_nonneg"),
        Index("ix_pos_sale_lines_sale", "sale_id"),
        {"schema": "pos"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sale_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pos.pos_sales.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    sale: Mapped[PosSale] = relationship(back_populates="lines")

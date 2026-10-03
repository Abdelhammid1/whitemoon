"""Delivery slots, shipments, and delivery shortages — EPIC 9.

Schema `logistics`. `Shipment.status` is a single abstraction over both the
internal fleet and external carriers (US-9.2 impl note), so the rest of the
system tracks delivery the same way regardless of who carries it.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..common.base_model import Base, TimestampMixin

CARRIER_TYPES = ("internal", "external")
SHIPMENT_STATUSES = ("scheduled", "shipped", "in_transit", "delivered", "failed")


class DeliverySlot(Base, TimestampMixin):
    """A bookable delivery window with a hard capacity (US-9.1)."""

    __tablename__ = "delivery_slots"
    __table_args__ = (
        UniqueConstraint("slot_date", "window", name="uq_delivery_slots_date_window"),
        CheckConstraint("capacity > 0", name="ck_delivery_slots_capacity_positive"),
        CheckConstraint("booked >= 0", name="ck_delivery_slots_booked_nonneg"),
        CheckConstraint("booked <= capacity", name="ck_delivery_slots_booked_lte_capacity"),
        Index("ix_delivery_slots_date", "slot_date"),
        {"schema": "logistics"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    window: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. "09:00-11:00"
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    booked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Shipment(Base, TimestampMixin):
    __tablename__ = "shipments"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_shipments_order"),
        CheckConstraint("carrier_type in ('internal','external')", name="ck_shipments_carrier"),
        CheckConstraint(
            "status in ('scheduled','shipped','in_transit','delivered','failed')",
            name="ck_shipments_status",
        ),
        Index("ix_shipments_status", "status"),
        {"schema": "logistics"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("commerce.orders.id"), nullable=False
    )
    slot_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("logistics.delivery_slots.id")
    )
    carrier_type: Mapped[str] = mapped_column(String(10), nullable=False, default="internal")
    carrier_ref: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="scheduled")
    current_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    current_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    confirmation_code: Mapped[str] = mapped_column(String(12), nullable=False)
    signature: Mapped[str | None] = mapped_column(String(2000))
    delivered_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id")
    )
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    shortages: Mapped[list[DeliveryShortage]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan", order_by="DeliveryShortage.id"
    )


class DeliveryShortage(Base):
    """A shortage found at delivery, with its photo — the returns-log entry
    (US-9.3). Automatically tied to its shipment."""

    __tablename__ = "delivery_shortages"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_delivery_shortages_qty_positive"),
        Index("ix_delivery_shortages_shipment", "shipment_id"),
        {"schema": "logistics"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("logistics.shipments.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(500))
    note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    shipment: Mapped[Shipment] = relationship(back_populates="shortages")

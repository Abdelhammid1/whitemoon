"""Commerce domain — EPIC 1 marketplace (Phase 4).

Design rules enforced here:
- The catalog is supplier-agnostic (inventory.products); a cart item points
  at a specific `supplier_offer`, but customer-facing responses never expose
  the supplier id (US-1.1).
- A unified cart spans multiple suppliers; checkout splits it into one
  `order_sub_order` per supplier, invisible to the customer (US-1.2).
- Price-lock (US-1.6): adding an item locks the offer's price for the
  reserved quantity until the hold expires or the order is placed. A
  supplier may lower a locked price but never raise it while a lock is live.
- Money is NUMERIC(18,4) + `currency = 'EGP'` CHECK everywhere.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
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

CART_STATUSES = ("active", "checked_out", "abandoned")
ORDER_STATUSES = ("pending", "confirmed", "cancelled", "fulfilled")
PAYMENT_MODES = ("cash", "deferred")
RFQ_STATUSES = ("open", "closed", "awarded", "cancelled")
INITIATOR_TYPES = ("customer", "supplier")


# ---------------------------------------------------------------- Cart


class Cart(Base, TimestampMixin):
    __tablename__ = "carts"
    __table_args__ = (
        CheckConstraint(
            "status in ('active','checked_out','abandoned')", name="ck_carts_status"
        ),
        Index("ix_carts_customer", "customer_id"),
        {"schema": "commerce"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")

    items: Mapped[list[CartItem]] = relationship(
        back_populates="cart", cascade="all, delete-orphan", order_by="CartItem.id"
    )


class CartItem(Base, TimestampMixin):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "supplier_offer_id", name="uq_cart_items_offer"),
        CheckConstraint("qty > 0", name="ck_cart_items_qty_positive"),
        {"schema": "commerce"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cart_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("commerce.carts.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    supplier_offer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.supplier_offers.id"), nullable=False
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    cart: Mapped[Cart] = relationship(back_populates="items")


# ---------------------------------------------------------------- Price locks


class PriceLock(Base, TimestampMixin):
    """A locked price for a reserved quantity (US-1.6)."""

    __tablename__ = "price_locks"
    __table_args__ = (
        CheckConstraint("locked_qty > 0", name="ck_price_locks_qty_positive"),
        CheckConstraint("locked_price > 0", name="ck_price_locks_price_positive"),
        CheckConstraint("currency = 'EGP'", name="ck_price_locks_currency_egp"),
        Index("ix_price_locks_offer_active", "supplier_offer_id", "released_at"),
        {"schema": "commerce"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    supplier_offer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.supplier_offers.id"), nullable=False
    )
    cart_item_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("commerce.cart_items.id")
    )
    locked_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    locked_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------- Orders


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("number", name="uq_orders_number"),
        CheckConstraint(
            "status in ('pending','confirmed','cancelled','fulfilled')",
            name="ck_orders_status",
        ),
        CheckConstraint(
            "payment_mode in ('cash','deferred')", name="ck_orders_payment_mode"
        ),
        CheckConstraint("currency = 'EGP'", name="ck_orders_currency_egp"),
        Index("ix_orders_customer", "customer_id"),
        {"schema": "commerce"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    payment_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    total_cash: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_deferred: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    credit_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    journal_entry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("accounting.journal_entries.id")
    )

    sub_orders: Mapped[list[OrderSubOrder]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderSubOrder.id"
    )


class OrderSubOrder(Base):
    """One per supplier within a unified order — invisible to the customer."""

    __tablename__ = "order_sub_orders"
    __table_args__ = (
        CheckConstraint("currency = 'EGP'", name="ck_order_sub_orders_currency_egp"),
        Index("ix_order_sub_orders_order", "order_id"),
        {"schema": "commerce"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("commerce.orders.id"), nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )

    order: Mapped[Order] = relationship(back_populates="sub_orders")
    lines: Mapped[list[OrderLine]] = relationship(
        back_populates="sub_order", cascade="all, delete-orphan", order_by="OrderLine.id"
    )


class OrderLine(Base):
    __tablename__ = "order_lines"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_order_lines_qty_positive"),
        CheckConstraint("currency = 'EGP'", name="ck_order_lines_currency_egp"),
        {"schema": "commerce"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sub_order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("commerce.order_sub_orders.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    supplier_offer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.supplier_offers.id"), nullable=False
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )

    sub_order: Mapped[OrderSubOrder] = relationship(back_populates="lines")


# ---------------------------------------------------------------- RFQ


class Rfq(Base, TimestampMixin):
    __tablename__ = "rfqs"
    __table_args__ = (
        UniqueConstraint("number", name="uq_rfqs_number"),
        CheckConstraint(
            "status in ('open','closed','awarded','cancelled')", name="ck_rfqs_status"
        ),
        CheckConstraint(
            "initiator_type in ('customer','supplier')", name="ck_rfqs_initiator_type"
        ),
        CheckConstraint("qty > 0", name="ck_rfqs_qty_positive"),
        {"schema": "commerce"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    initiator_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    initiator_type: Mapped[str] = mapped_column(String(10), nullable=False)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date)
    qualification_requirements: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    awarded_offer_id: Mapped[int | None] = mapped_column(BigInteger)

    offers: Mapped[list[RfqOffer]] = relationship(
        back_populates="rfq", cascade="all, delete-orphan", order_by="RfqOffer.unit_price"
    )


class RfqOffer(Base, TimestampMixin):
    __tablename__ = "rfq_offers"
    __table_args__ = (
        UniqueConstraint("rfq_id", "supplier_id", name="uq_rfq_offers_supplier"),
        CheckConstraint("unit_price > 0", name="ck_rfq_offers_price_positive"),
        CheckConstraint("currency = 'EGP'", name="ck_rfq_offers_currency_egp"),
        {"schema": "commerce"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rfq_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("commerce.rfqs.id"), nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    moq: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    rfq: Mapped[Rfq] = relationship(back_populates="offers")

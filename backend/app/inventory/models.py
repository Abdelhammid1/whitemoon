"""Inventory domain — EPIC 4.

Design rules enforced here (docs/01-db-schema-skeleton.md + ملاحظات EPIC 4):
- Products are **supplier-agnostic** (single catalog). Suppliers attach
  offers; the "best price" is derived server-side.
- Stock is **per-supplier, per-location**. Suppliers never see other
  suppliers' balances.
- Transfer orders are a **first-class entity** with a number, not a
  column on inventory moves (US-4.2 ملاحظة التنفيذية).
- Shortages record the responsible party (supplier / channel partner /
  none) so the accounting trigger can debit the right account (US-4.4).
- Qty is NUMERIC(18,4). Food is often fractional (kg); fractional qty
  must not round silently.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
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

CATEGORIES = (
    "food",
    "clothing",
    "electronics",
    "home",
    "beauty",
    "construction",
    "stationery",
    "automotive",
    "other",
)
# Arabic labels — single source for the UI (served by GET /inventory/categories).
CATEGORY_LABELS = {
    "food": "غذائية",
    "clothing": "ملابس",
    "electronics": "إلكترونيات",
    "home": "أدوات منزلية",
    "beauty": "عناية وتجميل",
    "construction": "مواد بناء",
    "stationery": "قرطاسية",
    "automotive": "قطع غيار",
    "other": "أخرى",
}
LOCATION_TYPES = ("supplier", "channel_partner", "in_transit", "customer_hold")
# Arabic labels — single source for the UI (served by GET /inventory/location-types).
LOCATION_TYPE_LABELS = {
    "supplier": "مخزن المورد",
    "channel_partner": "عهدة وكيل/فرع",
    "in_transit": "في الطريق",
    "customer_hold": "حجز عميل",
}
TRANSFER_STATUSES = ("draft", "issued", "received", "cancelled")
SHORTAGE_STATUSES = ("pending", "resolved", "rejected")
RESPONSIBLE_PARTY_TYPES = ("supplier", "channel_partner", "unallocated")


# ---------------------------------------------------------------- Products


class Product(Base, TimestampMixin):
    """Supplier-agnostic catalog item curated by admins."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_products_sku"),
        CheckConstraint(
            "category in ('food','clothing','electronics','home','beauty',"
            "'construction','stationery','automotive','other')",
            name="ck_products_category",
        ),
        {"schema": "inventory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sku: Mapped[str] = mapped_column(String(60), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="piece")
    eta_code: Mapped[str | None] = mapped_column(String(60))
    # ETA e-invoicing readiness at the item level (EPIC 11, US-11.1): the item
    # is structurally ready to be reported to the Egyptian Tax Authority.
    eta_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    food_expiry_tracked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id")
    )
    # Richer catalog fields (T-10). Category stays food/clothing; subcategory
    # is free text for finer classification.
    subcategory: Mapped[str | None] = mapped_column(String(120))
    brand: Mapped[str | None] = mapped_column(String(120))
    barcode: Mapped[str | None] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(String(2000))
    image_url: Mapped[str | None] = mapped_column(String(500))

    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductVariant.id"
    )


class ProductVariant(Base, TimestampMixin):
    """A sellable variant of a product — size/color with its own SKU/barcode
    (T-10). Stock/pricing still key off the parent product in this version."""

    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_product_variants_sku"),
        Index("ix_product_variants_product", "product_id"),
        {"schema": "inventory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(60), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(60))
    size: Mapped[str | None] = mapped_column(String(60))
    color: Mapped[str | None] = mapped_column(String(60))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    product: Mapped[Product] = relationship(back_populates="variants")


# ---------------------------------------------------------------- Supplier offers


class SupplierOffer(Base, TimestampMixin):
    """One supplier's offer for a given product.

    Multiple suppliers can offer the same product; the "best price"
    (lowest active offer with enough qty) is picked server-side only.
    """

    __tablename__ = "supplier_offers"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "supplier_id", name="uq_supplier_offers_product_supplier"
        ),
        CheckConstraint("unit_price > 0", name="ck_supplier_offers_price_positive"),
        CheckConstraint("moq >= 0", name="ck_supplier_offers_moq_nonneg"),
        CheckConstraint(
            "currency = 'EGP'", name="ck_supplier_offers_currency_egp"
        ),
        Index("ix_supplier_offers_product", "product_id"),
        {"schema": "inventory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    moq: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    # Price-lock support for Phase 4 — a locked offer rejects price raises
    # on the locked qty.
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    product: Mapped[Product] = relationship()


# ---------------------------------------------------------------- Stock balances


class StockBalance(Base, TimestampMixin):
    """Per-supplier, per-location on-hand + reserved.

    `location_id` is nullable only for `location_type='supplier'`, where
    the balance represents the supplier's own warehouse.
    """

    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint(
            "supplier_id",
            "product_id",
            "location_type",
            "location_id",
            name="uq_stock_balances_slot",
        ),
        CheckConstraint(
            "location_type in ('supplier','channel_partner','in_transit','customer_hold')",
            name="ck_stock_balances_location_type",
        ),
        CheckConstraint("on_hand >= 0", name="ck_stock_balances_on_hand_nonneg"),
        CheckConstraint("reserved >= 0", name="ck_stock_balances_reserved_nonneg"),
        CheckConstraint(
            "reserved <= on_hand", name="ck_stock_balances_reserved_lte_on_hand"
        ),
        Index("ix_stock_balances_product", "product_id"),
        {"schema": "inventory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    location_type: Mapped[str] = mapped_column(String(20), nullable=False)
    location_id: Mapped[int | None] = mapped_column(BigInteger)
    on_hand: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    reserved: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    reorder_point: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))

    product: Mapped[Product] = relationship()


# ---------------------------------------------------------------- Transfer orders


class TransferOrder(Base, TimestampMixin):
    """First-class entity. Every physical movement of stock has one.

    Lifecycle: draft → issued (stock leaves source) → received (stock
    arrives at destination). Each state change posts a matching journal
    entry via the accounting event-map.
    """

    __tablename__ = "transfer_orders"
    __table_args__ = (
        UniqueConstraint("number", name="uq_transfer_orders_number"),
        CheckConstraint(
            "status in ('draft','issued','received','cancelled')",
            name="ck_transfer_orders_status",
        ),
        CheckConstraint(
            "from_location_type in ('supplier','channel_partner','in_transit','customer_hold')",
            name="ck_transfer_orders_from_location_type",
        ),
        CheckConstraint(
            "to_location_type in ('supplier','channel_partner','in_transit','customer_hold')",
            name="ck_transfer_orders_to_location_type",
        ),
        {"schema": "inventory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    from_location_type: Mapped[str] = mapped_column(String(20), nullable=False)
    from_location_id: Mapped[int | None] = mapped_column(BigInteger)
    to_location_type: Mapped[str] = mapped_column(String(20), nullable=False)
    to_location_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    initiated_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issued_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id")
    )
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id")
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    issue_entry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("accounting.journal_entries.id")
    )
    receive_entry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("accounting.journal_entries.id")
    )

    lines: Mapped[list[TransferOrderLine]] = relationship(
        back_populates="transfer_order",
        cascade="all, delete-orphan",
        order_by="TransferOrderLine.id",
    )


class TransferOrderLine(Base):
    __tablename__ = "transfer_order_lines"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_transfer_order_lines_qty_positive"),
        CheckConstraint(
            "unit_cost >= 0", name="ck_transfer_order_lines_unit_cost_nonneg"
        ),
        {"schema": "inventory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    transfer_order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.transfer_orders.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    transfer_order: Mapped[TransferOrder] = relationship(back_populates="lines")


# ---------------------------------------------------------------- Batches (expiry)


class Batch(Base, TimestampMixin):
    """Optional expiry tracking for food (EPIC 4 ميزة اضافية).

    v1 stores the batch record; routes that need to enforce FEFO can be
    added incrementally without a schema change.
    """

    __tablename__ = "batches"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "supplier_id", "batch_code", name="uq_batches_identity"
        ),
        CheckConstraint("qty_on_hand >= 0", name="ck_batches_qty_nonneg"),
        {"schema": "inventory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    batch_code: Mapped[str] = mapped_column(String(60), nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    qty_on_hand: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)


# ---------------------------------------------------------------- Shortages (US-4.4)


class Shortage(Base, TimestampMixin):
    """Nowhere-near-the-signed-manifest discrepancy.

    `responsible_party_type` chooses the shortage.resolved.* event posted
    when the shortage is resolved. 'unallocated' means the loss hits
    5310 instead of a specific party's receivable.
    """

    __tablename__ = "shortages"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_shortages_qty_positive"),
        CheckConstraint(
            "status in ('pending','resolved','rejected')",
            name="ck_shortages_status",
        ),
        CheckConstraint(
            "responsible_party_type is null or "
            "responsible_party_type in ('supplier','channel_partner','unallocated')",
            name="ck_shortages_responsible_party_type",
        ),
        {"schema": "inventory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    reporter_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    transfer_order_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("inventory.transfer_orders.id")
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.products.id"), nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    responsible_party_type: Mapped[str | None] = mapped_column(String(20))
    responsible_party_id: Mapped[int | None] = mapped_column(BigInteger)
    evidence_s3_keys: Mapped[list[str] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    resolution_notes: Mapped[str | None] = mapped_column(String(1000))
    resolved_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    journal_entry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("accounting.journal_entries.id")
    )


# ---------------------------------------------------------------- Reorder alerts


class ReorderAlert(Base):
    """A low-stock alert in the escalation chain (US-4.3).

    Levels:
      1 — notify customer / branch at the depleting location
      2 — notify the regional agent
      3 — notify the company (admin)
      4 — notify the supplier (restock request)
    """

    __tablename__ = "reorder_alerts"
    __table_args__ = (
        CheckConstraint("level between 1 and 4", name="ck_reorder_alerts_level"),
        Index(
            "ix_reorder_alerts_stock_balance", "stock_balance_id", "level"
        ),
        {"schema": "inventory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_balance_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.stock_balances.id"), nullable=False
    )
    level: Mapped[int] = mapped_column(nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id")
    )
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

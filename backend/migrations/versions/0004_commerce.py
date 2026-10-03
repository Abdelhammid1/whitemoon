"""commerce schema — carts, price locks, orders, sub-orders, lines, RFQ.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS commerce")

    op.create_table(
        "carts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'active'")),
        *_ts(),
        sa.CheckConstraint("status in ('active','checked_out','abandoned')", name="ck_carts_status"),
        schema="commerce",
    )
    op.create_index("ix_carts_customer", "carts", ["customer_id"], schema="commerce")

    op.create_table(
        "cart_items",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("cart_id", sa.BigInteger(), sa.ForeignKey("commerce.carts.id"), nullable=False),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("inventory.products.id"), nullable=False),
        sa.Column("supplier_offer_id", sa.BigInteger(), sa.ForeignKey("inventory.supplier_offers.id"), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        *_ts(),
        sa.UniqueConstraint("cart_id", "supplier_offer_id", name="uq_cart_items_offer"),
        sa.CheckConstraint("qty > 0", name="ck_cart_items_qty_positive"),
        schema="commerce",
    )

    op.create_table(
        "price_locks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("supplier_offer_id", sa.BigInteger(), sa.ForeignKey("inventory.supplier_offers.id"), nullable=False),
        sa.Column("cart_item_id", sa.BigInteger(), sa.ForeignKey("commerce.cart_items.id"), nullable=True),
        sa.Column("locked_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("locked_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.CheckConstraint("locked_qty > 0", name="ck_price_locks_qty_positive"),
        sa.CheckConstraint("locked_price > 0", name="ck_price_locks_price_positive"),
        sa.CheckConstraint("currency = 'EGP'", name="ck_price_locks_currency_egp"),
        schema="commerce",
    )
    op.create_index("ix_price_locks_offer_active", "price_locks", ["supplier_offer_id", "released_at"], schema="commerce")

    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("number", sa.String(40), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("payment_mode", sa.String(10), nullable=False),
        sa.Column("total_cash", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("total_deferred", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("placed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("credit_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("journal_entry_id", sa.BigInteger(), sa.ForeignKey("accounting.journal_entries.id"), nullable=True),
        *_ts(),
        sa.UniqueConstraint("number", name="uq_orders_number"),
        sa.CheckConstraint("status in ('pending','confirmed','cancelled','fulfilled')", name="ck_orders_status"),
        sa.CheckConstraint("payment_mode in ('cash','deferred')", name="ck_orders_payment_mode"),
        sa.CheckConstraint("currency = 'EGP'", name="ck_orders_currency_egp"),
        schema="commerce",
    )
    op.create_index("ix_orders_customer", "orders", ["customer_id"], schema="commerce")

    op.create_table(
        "order_sub_orders",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("order_id", sa.BigInteger(), sa.ForeignKey("commerce.orders.id"), nullable=False),
        sa.Column("supplier_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.CheckConstraint("currency = 'EGP'", name="ck_order_sub_orders_currency_egp"),
        schema="commerce",
    )
    op.create_index("ix_order_sub_orders_order", "order_sub_orders", ["order_id"], schema="commerce")

    op.create_table(
        "order_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("sub_order_id", sa.BigInteger(), sa.ForeignKey("commerce.order_sub_orders.id"), nullable=False),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("inventory.products.id"), nullable=False),
        sa.Column("supplier_offer_id", sa.BigInteger(), sa.ForeignKey("inventory.supplier_offers.id"), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.CheckConstraint("qty > 0", name="ck_order_lines_qty_positive"),
        sa.CheckConstraint("currency = 'EGP'", name="ck_order_lines_currency_egp"),
        schema="commerce",
    )

    op.create_table(
        "rfqs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("number", sa.String(40), nullable=False),
        sa.Column("initiator_user_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("initiator_type", sa.String(10), nullable=False),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("inventory.products.id"), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("qualification_requirements", sa.String(1000), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'open'")),
        sa.Column("awarded_offer_id", sa.BigInteger(), nullable=True),
        *_ts(),
        sa.UniqueConstraint("number", name="uq_rfqs_number"),
        sa.CheckConstraint("status in ('open','closed','awarded','cancelled')", name="ck_rfqs_status"),
        sa.CheckConstraint("initiator_type in ('customer','supplier')", name="ck_rfqs_initiator_type"),
        sa.CheckConstraint("qty > 0", name="ck_rfqs_qty_positive"),
        schema="commerce",
    )

    op.create_table(
        "rfq_offers",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("rfq_id", sa.BigInteger(), sa.ForeignKey("commerce.rfqs.id"), nullable=False),
        sa.Column("supplier_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("moq", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        *_ts(),
        sa.UniqueConstraint("rfq_id", "supplier_id", name="uq_rfq_offers_supplier"),
        sa.CheckConstraint("unit_price > 0", name="ck_rfq_offers_price_positive"),
        sa.CheckConstraint("currency = 'EGP'", name="ck_rfq_offers_currency_egp"),
        schema="commerce",
    )


def downgrade() -> None:
    op.drop_table("rfq_offers", schema="commerce")
    op.drop_table("rfqs", schema="commerce")
    op.drop_table("order_lines", schema="commerce")
    op.drop_index("ix_order_sub_orders_order", table_name="order_sub_orders", schema="commerce")
    op.drop_table("order_sub_orders", schema="commerce")
    op.drop_index("ix_orders_customer", table_name="orders", schema="commerce")
    op.drop_table("orders", schema="commerce")
    op.drop_index("ix_price_locks_offer_active", table_name="price_locks", schema="commerce")
    op.drop_table("price_locks", schema="commerce")
    op.drop_table("cart_items", schema="commerce")
    op.drop_index("ix_carts_customer", table_name="carts", schema="commerce")
    op.drop_table("carts", schema="commerce")
    op.execute("DROP SCHEMA IF EXISTS commerce")

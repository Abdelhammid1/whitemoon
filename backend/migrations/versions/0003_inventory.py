"""inventory schema — products, offers, stock, transfers, batches, shortages, reorder alerts.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS inventory")

    _ts = (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ----- inventory.products
    op.create_table(
        "products",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("sku", sa.String(60), nullable=False),
        sa.Column("name_ar", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=True),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column(
            "unit",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'piece'"),
        ),
        sa.Column("eta_code", sa.String(60), nullable=True),
        sa.Column(
            "food_expiry_tracked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_by",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
        ),
        *_ts,
        sa.UniqueConstraint("sku", name="uq_products_sku"),
        sa.CheckConstraint(
            "category in ('food','clothing')", name="ck_products_category"
        ),
        schema="inventory",
    )

    # ----- inventory.supplier_offers
    op.create_table(
        "supplier_offers",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("inventory.products.id"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "moq", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default=sa.text("'EGP'"),
        ),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        *_ts,
        sa.UniqueConstraint(
            "product_id", "supplier_id", name="uq_supplier_offers_product_supplier"
        ),
        sa.CheckConstraint(
            "unit_price > 0", name="ck_supplier_offers_price_positive"
        ),
        sa.CheckConstraint("moq >= 0", name="ck_supplier_offers_moq_nonneg"),
        sa.CheckConstraint(
            "currency = 'EGP'", name="ck_supplier_offers_currency_egp"
        ),
        schema="inventory",
    )
    op.create_index(
        "ix_supplier_offers_product",
        "supplier_offers",
        ["product_id"],
        schema="inventory",
    )

    # ----- inventory.stock_balances
    op.create_table(
        "stock_balances",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "supplier_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("inventory.products.id"),
            nullable=False,
        ),
        sa.Column("location_type", sa.String(20), nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "on_hand",
            sa.Numeric(18, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "reserved",
            sa.Numeric(18, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("reorder_point", sa.Numeric(18, 4), nullable=True),
        *_ts,
        sa.UniqueConstraint(
            "supplier_id",
            "product_id",
            "location_type",
            "location_id",
            name="uq_stock_balances_slot",
        ),
        sa.CheckConstraint(
            "location_type in ('supplier','channel_partner','in_transit','customer_hold')",
            name="ck_stock_balances_location_type",
        ),
        sa.CheckConstraint("on_hand >= 0", name="ck_stock_balances_on_hand_nonneg"),
        sa.CheckConstraint(
            "reserved >= 0", name="ck_stock_balances_reserved_nonneg"
        ),
        sa.CheckConstraint(
            "reserved <= on_hand", name="ck_stock_balances_reserved_lte_on_hand"
        ),
        schema="inventory",
    )
    op.create_index(
        "ix_stock_balances_product",
        "stock_balances",
        ["product_id"],
        schema="inventory",
    )

    # ----- inventory.transfer_orders
    op.create_table(
        "transfer_orders",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("number", sa.String(40), nullable=False),
        sa.Column(
            "supplier_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("from_location_type", sa.String(20), nullable=False),
        sa.Column("from_location_id", sa.BigInteger(), nullable=True),
        sa.Column("to_location_type", sa.String(20), nullable=False),
        sa.Column("to_location_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "initiated_by",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "issued_by",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
        ),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "received_by",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "issue_entry_id",
            sa.BigInteger(),
            sa.ForeignKey("accounting.journal_entries.id"),
            nullable=True,
        ),
        sa.Column(
            "receive_entry_id",
            sa.BigInteger(),
            sa.ForeignKey("accounting.journal_entries.id"),
            nullable=True,
        ),
        *_ts,
        sa.UniqueConstraint("number", name="uq_transfer_orders_number"),
        sa.CheckConstraint(
            "status in ('draft','issued','received','cancelled')",
            name="ck_transfer_orders_status",
        ),
        sa.CheckConstraint(
            "from_location_type in ('supplier','channel_partner','in_transit','customer_hold')",
            name="ck_transfer_orders_from_location_type",
        ),
        sa.CheckConstraint(
            "to_location_type in ('supplier','channel_partner','in_transit','customer_hold')",
            name="ck_transfer_orders_to_location_type",
        ),
        schema="inventory",
    )

    # ----- inventory.transfer_order_lines
    op.create_table(
        "transfer_order_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "transfer_order_id",
            sa.BigInteger(),
            sa.ForeignKey("inventory.transfer_orders.id"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("inventory.products.id"),
            nullable=False,
        ),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.CheckConstraint("qty > 0", name="ck_transfer_order_lines_qty_positive"),
        sa.CheckConstraint(
            "unit_cost >= 0", name="ck_transfer_order_lines_unit_cost_nonneg"
        ),
        schema="inventory",
    )

    # ----- inventory.batches
    op.create_table(
        "batches",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("inventory.products.id"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("batch_code", sa.String(60), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("qty_on_hand", sa.Numeric(18, 4), nullable=False),
        *_ts,
        sa.UniqueConstraint(
            "product_id", "supplier_id", "batch_code", name="uq_batches_identity"
        ),
        sa.CheckConstraint("qty_on_hand >= 0", name="ck_batches_qty_nonneg"),
        schema="inventory",
    )

    # ----- inventory.shortages
    op.create_table(
        "shortages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "reporter_user_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column(
            "transfer_order_id",
            sa.BigInteger(),
            sa.ForeignKey("inventory.transfer_orders.id"),
            nullable=True,
        ),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("inventory.products.id"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("responsible_party_type", sa.String(20), nullable=True),
        sa.Column("responsible_party_id", sa.BigInteger(), nullable=True),
        sa.Column("evidence_s3_keys", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("resolution_notes", sa.String(1000), nullable=True),
        sa.Column(
            "resolved_by",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "journal_entry_id",
            sa.BigInteger(),
            sa.ForeignKey("accounting.journal_entries.id"),
            nullable=True,
        ),
        *_ts,
        sa.CheckConstraint("qty > 0", name="ck_shortages_qty_positive"),
        sa.CheckConstraint(
            "status in ('pending','resolved','rejected')",
            name="ck_shortages_status",
        ),
        sa.CheckConstraint(
            "responsible_party_type is null or "
            "responsible_party_type in ('supplier','channel_partner','unallocated')",
            name="ck_shortages_responsible_party_type",
        ),
        schema="inventory",
    )

    # ----- inventory.reorder_alerts
    op.create_table(
        "reorder_alerts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "stock_balance_id",
            sa.BigInteger(),
            sa.ForeignKey("inventory.stock_balances.id"),
            nullable=False,
        ),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "acknowledged_by",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
        ),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.CheckConstraint("level between 1 and 4", name="ck_reorder_alerts_level"),
        schema="inventory",
    )
    op.create_index(
        "ix_reorder_alerts_stock_balance",
        "reorder_alerts",
        ["stock_balance_id", "level"],
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reorder_alerts_stock_balance",
        table_name="reorder_alerts",
        schema="inventory",
    )
    op.drop_table("reorder_alerts", schema="inventory")
    op.drop_table("shortages", schema="inventory")
    op.drop_table("batches", schema="inventory")
    op.drop_table("transfer_order_lines", schema="inventory")
    op.drop_table("transfer_orders", schema="inventory")
    op.drop_index(
        "ix_stock_balances_product",
        table_name="stock_balances",
        schema="inventory",
    )
    op.drop_table("stock_balances", schema="inventory")
    op.drop_index(
        "ix_supplier_offers_product",
        table_name="supplier_offers",
        schema="inventory",
    )
    op.drop_table("supplier_offers", schema="inventory")
    op.drop_table("products", schema="inventory")
    op.execute("DROP SCHEMA IF EXISTS inventory")

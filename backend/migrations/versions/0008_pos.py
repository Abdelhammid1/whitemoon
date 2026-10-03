"""pos schema — sales, sale lines, settlement batches.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS pos")

    op.create_table(
        "pos_batches",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("posted_by", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sale_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("total", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("journal_entry_id", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("currency = 'EGP'", name="ck_pos_batches_currency_egp"),
        schema="pos",
    )

    op.create_table(
        "pos_sales",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("number", sa.String(40), nullable=False),
        sa.Column("cashier_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("location_type", sa.String(20), nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=True),
        sa.Column("total", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("status", sa.String(10), nullable=False, server_default=sa.text("'completed'")),
        sa.Column("posted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("batch_id", sa.BigInteger(), sa.ForeignKey("pos.pos_batches.id"), nullable=True),
        sa.Column("sold_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        *_ts(),
        sa.UniqueConstraint("number", name="uq_pos_sales_number"),
        sa.CheckConstraint("total >= 0", name="ck_pos_sales_total_nonneg"),
        sa.CheckConstraint("status in ('completed','voided')", name="ck_pos_sales_status"),
        sa.CheckConstraint(
            "location_type in ('supplier','channel_partner','in_transit','customer_hold')",
            name="ck_pos_sales_location_type",
        ),
        sa.CheckConstraint("currency = 'EGP'", name="ck_pos_sales_currency_egp"),
        schema="pos",
    )
    op.create_index("ix_pos_sales_posted", "pos_sales", ["posted", "status"], schema="pos")

    op.create_table(
        "pos_sale_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("sale_id", sa.BigInteger(), sa.ForeignKey("pos.pos_sales.id"), nullable=False),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("inventory.products.id"), nullable=False),
        sa.Column("supplier_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 4), nullable=False),
        sa.CheckConstraint("qty > 0", name="ck_pos_sale_lines_qty_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_pos_sale_lines_unit_price_nonneg"),
        schema="pos",
    )
    op.create_index("ix_pos_sale_lines_sale", "pos_sale_lines", ["sale_id"], schema="pos")


def downgrade() -> None:
    op.drop_index("ix_pos_sale_lines_sale", table_name="pos_sale_lines", schema="pos")
    op.drop_table("pos_sale_lines", schema="pos")
    op.drop_index("ix_pos_sales_posted", table_name="pos_sales", schema="pos")
    op.drop_table("pos_sales", schema="pos")
    op.drop_table("pos_batches", schema="pos")
    op.execute("DROP SCHEMA IF EXISTS pos")

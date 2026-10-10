"""Unified supplier products: offer discounts + coding requests (T-30).

Adds promotional discount columns to inventory.supplier_offers and a new
inventory.product_coding_requests table (suppliers request a new item be coded;
the full admin queue is T-31). All additive; discount columns default to 'none'.

Revision ID: 0031
Revises: 0030
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031"
down_revision: str | Sequence[str] | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "supplier_offers",
        sa.Column("discount_kind", sa.String(10), nullable=False, server_default="none"),
        schema="inventory",
    )
    op.add_column("supplier_offers", sa.Column("discount_value", sa.Numeric(18, 4)), schema="inventory")
    op.add_column("supplier_offers", sa.Column("discount_start", sa.Date()), schema="inventory")
    op.add_column("supplier_offers", sa.Column("discount_end", sa.Date()), schema="inventory")

    op.create_table(
        "product_coding_requests",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("supplier_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("barcode", sa.String(60)),
        sa.Column("brand", sa.String(120)),
        sa.Column("category", sa.String(40)),
        sa.Column("image_url", sa.String(500)),
        sa.Column("note", sa.String(1000)),
        sa.Column("status", sa.String(12), nullable=False, server_default="new"),
        sa.Column("reject_reason", sa.String(1000)),
        sa.Column("product_id", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status in ('new','in_review','coded','rejected')", name="ck_product_coding_requests_status"),
        schema="inventory",
    )
    op.create_index("ix_product_coding_requests_status", "product_coding_requests", ["status"], schema="inventory")


def downgrade() -> None:
    op.drop_table("product_coding_requests", schema="inventory")
    op.drop_column("supplier_offers", "discount_end", schema="inventory")
    op.drop_column("supplier_offers", "discount_start", schema="inventory")
    op.drop_column("supplier_offers", "discount_value", schema="inventory")
    op.drop_column("supplier_offers", "discount_kind", schema="inventory")

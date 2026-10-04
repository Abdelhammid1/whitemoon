"""richer product fields + product variants (T-10).

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | Sequence[str] | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for col in (
        sa.Column("subcategory", sa.String(120), nullable=True),
        sa.Column("brand", sa.String(120), nullable=True),
        sa.Column("barcode", sa.String(60), nullable=True),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
    ):
        op.add_column("products", col, schema="inventory")

    op.create_table(
        "product_variants",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("inventory.products.id"), nullable=False),
        sa.Column("sku", sa.String(60), nullable=False),
        sa.Column("barcode", sa.String(60), nullable=True),
        sa.Column("size", sa.String(60), nullable=True),
        sa.Column("color", sa.String(60), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("sku", name="uq_product_variants_sku"),
        schema="inventory",
    )
    op.create_index("ix_product_variants_product", "product_variants", ["product_id"], schema="inventory")


def downgrade() -> None:
    op.drop_index("ix_product_variants_product", table_name="product_variants", schema="inventory")
    op.drop_table("product_variants", schema="inventory")
    for name in ("image_url", "description", "barcode", "brand", "subcategory"):
        op.drop_column("products", name, schema="inventory")

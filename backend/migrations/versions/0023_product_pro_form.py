"""Professional product form fields (T-14).

Adds product lifecycle status, reference pricing, tax + ETA classification,
a variant pack attribute, a batch production date, and a product image gallery.

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | Sequence[str] | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("status", sa.String(length=12), nullable=False, server_default="active"),
        schema="inventory",
    )
    op.add_column("products", sa.Column("wholesale_price", sa.Numeric(18, 4)), schema="inventory")
    op.add_column("products", sa.Column("deferred_price", sa.Numeric(18, 4)), schema="inventory")
    op.add_column("products", sa.Column("default_moq", sa.Numeric(18, 4)), schema="inventory")
    op.add_column("products", sa.Column("tax_rate", sa.Numeric(6, 3)), schema="inventory")
    op.add_column("products", sa.Column("eta_code_type", sa.String(length=10)), schema="inventory")
    # Backfill status from the existing is_active flag.
    op.execute("UPDATE inventory.products SET status='suspended' WHERE is_active = false")
    op.create_check_constraint(
        "ck_products_status",
        "products",
        "status in ('active','draft','suspended')",
        schema="inventory",
    )

    op.add_column("product_variants", sa.Column("pack", sa.String(length=60)), schema="inventory")
    op.add_column("batches", sa.Column("production_date", sa.Date()), schema="inventory")

    op.create_table(
        "product_images",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("storage_key", sa.String(length=500)),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"], ["inventory.products.id"], name="fk_product_images_product_id_products"
        ),
        sa.Index("ix_product_images_product", "product_id"),
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_table("product_images", schema="inventory")
    op.drop_column("batches", "production_date", schema="inventory")
    op.drop_column("product_variants", "pack", schema="inventory")
    op.drop_constraint("ck_products_status", "products", schema="inventory", type_="check")
    for col in ("eta_code_type", "tax_rate", "default_moq", "deferred_price", "wholesale_price", "status"):
        op.drop_column("products", col, schema="inventory")

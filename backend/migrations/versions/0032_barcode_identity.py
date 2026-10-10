"""Barcode identity (T-31): unique barcode across products.

A product's global barcode (EAN-13 / UPC-A) is its identity and must be unique.
Enforced with a partial unique index (NULL barcodes — local products — are
exempt; they carry an auto WM-NNNNNN sku instead).

Revision ID: 0032
Revises: 0031
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032"
down_revision: str | Sequence[str] | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_products_barcode",
        "products",
        ["barcode"],
        unique=True,
        schema="inventory",
        postgresql_where=sa.text("barcode IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_products_barcode", table_name="products", schema="inventory")

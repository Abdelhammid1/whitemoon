"""Expand the product category vocabulary (T-10).

Replaces the two-value category CHECK (food/clothing) with the curated list
so products in other segments are no longer rejected.

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | Sequence[str] | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW = (
    "category in ('food','clothing','electronics','home','beauty',"
    "'construction','stationery','automotive','other')"
)
_OLD = "category in ('food','clothing')"


def upgrade() -> None:
    op.drop_constraint("ck_products_category", "products", schema="inventory", type_="check")
    op.create_check_constraint("ck_products_category", "products", _NEW, schema="inventory")


def downgrade() -> None:
    op.drop_constraint("ck_products_category", "products", schema="inventory", type_="check")
    op.create_check_constraint("ck_products_category", "products", _OLD, schema="inventory")

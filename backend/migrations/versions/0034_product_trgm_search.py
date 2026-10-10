"""Typo-tolerant product search (T-43): enable pg_trgm + a trigram GIN index on
products.name_ar so «طلب سريع» can match misspelled names via similarity().

Revision ID: 0034
Revises: 0033
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0034"
down_revision: str | Sequence[str] | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_name_ar_trgm "
        "ON inventory.products USING gin (name_ar gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS inventory.ix_products_name_ar_trgm")
    # Leave the pg_trgm extension in place — other objects may depend on it.

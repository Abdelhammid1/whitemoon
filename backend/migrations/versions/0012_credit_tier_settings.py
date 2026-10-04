"""credit tier settings — admin-configurable limits per colour (T-11).

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "credit_tier_settings",
        sa.Column("tier", sa.String(10), primary_key=True),
        sa.Column("credit_limit", sa.Numeric(18, 4), nullable=False),
        sa.Column("deferred_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("tier in ('white','green','yellow','red')", name="ck_tier_settings_tier"),
        sa.CheckConstraint("currency = 'EGP'", name="ck_tier_settings_currency_egp"),
        schema="sales",
    )
    # Seed the signed defaults.
    op.execute(
        "INSERT INTO sales.credit_tier_settings (tier, credit_limit, deferred_pct) VALUES "
        "('green', 500000, 100), ('white', 250000, 60), "
        "('yellow', 100000, 40), ('red', 0, 0)"
    )


def downgrade() -> None:
    op.drop_table("credit_tier_settings", schema="sales")

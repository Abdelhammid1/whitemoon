"""customer_credit_tiers: escalation floor for forced L3 downgrade (docs/04 §2).

Adds the escalation floor + its timestamp so a dunning downgrade persists
through recompute and recovers one step at a time (de-escalation).

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str | Sequence[str] | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer_credit_tiers",
        sa.Column("escalation_floor", sa.String(10), nullable=True),
        schema="sales",
    )
    op.add_column(
        "customer_credit_tiers",
        sa.Column("floor_set_at", sa.DateTime(timezone=True), nullable=True),
        schema="sales",
    )


def downgrade() -> None:
    op.drop_column("customer_credit_tiers", "floor_set_at", schema="sales")
    op.drop_column("customer_credit_tiers", "escalation_floor", schema="sales")

"""supplier minimum order value (T-03, US-4.5).

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | Sequence[str] | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "supplier_profiles",
        sa.Column("min_order_value", sa.Numeric(18, 4), nullable=False, server_default="0"),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_column("supplier_profiles", "min_order_value", schema="identity")

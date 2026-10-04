"""customer geo_area for territory scoping (T-01).

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer_profiles",
        sa.Column("geo_area", sa.String(200), nullable=True),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_column("customer_profiles", "geo_area", schema="identity")

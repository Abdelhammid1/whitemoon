"""compliance — products.eta_ready flag (EPIC 11, US-11.1).

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("eta_ready", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_column("products", "eta_ready", schema="inventory")

"""Remember-me device sessions (T-46): mark which refresh sessions are
"remembered" (shown on «أجهزتي») and track their last use.

Revision ID: 0035
Revises: 0034
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035"
down_revision: str | Sequence[str] | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("remembered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        schema="identity",
    )
    op.add_column(
        "sessions",
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_column("sessions", "last_used_at", schema="identity")
    op.drop_column("sessions", "remembered", schema="identity")

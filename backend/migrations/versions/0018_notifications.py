"""notifications schema — multi-channel notification center.

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | Sequence[str] | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS notifications")
    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("type", sa.String(40), nullable=False, server_default=sa.text("'system'")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("channel", sa.String(10), nullable=False, server_default=sa.text("'in_app'")),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("channel in ('in_app','sms','whatsapp','email')", name="ck_notifications_channel"),
        schema="notifications",
    )
    op.create_index("ix_notifications_user", "notifications", ["user_id", "is_read"], schema="notifications")


def downgrade() -> None:
    op.drop_index("ix_notifications_user", table_name="notifications", schema="notifications")
    op.drop_table("notifications", schema="notifications")
    op.execute("DROP SCHEMA IF EXISTS notifications")

"""System settings registry (T-37): tunable business constants + change log.

Two tables in the identity schema:
- `system_settings` — one row per overridden key (absent → registry default).
- `system_setting_changes` — append-only audit of every value change.

Revision ID: 0033
Revises: 0032
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033"
down_revision: str | Sequence[str] | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_by_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_id"], ["identity.users.id"], name="fk_system_settings_updated_by_id_users"),
        sa.PrimaryKeyConstraint("key", name="pk_system_settings"),
        schema="identity",
    )
    op.create_table(
        "system_setting_changes",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=False),
        sa.Column("changed_by_id", sa.BigInteger(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_id"], ["identity.users.id"], name="fk_system_setting_changes_changed_by_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_system_setting_changes"),
        schema="identity",
    )
    op.create_index(
        "ix_identity_system_setting_changes_key",
        "system_setting_changes",
        ["key"],
        schema="identity",
    )


def downgrade() -> None:
    op.drop_index("ix_identity_system_setting_changes_key", table_name="system_setting_changes", schema="identity")
    op.drop_table("system_setting_changes", schema="identity")
    op.drop_table("system_settings", schema="identity")

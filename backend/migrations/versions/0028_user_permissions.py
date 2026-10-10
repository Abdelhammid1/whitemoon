"""Per-user permission grants (delegation).

Lets an admin grant a specific permission (e.g. deferred.settings.manage) to a
chosen user without changing their role.

Revision ID: 0028
Revises: 0027
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: str | Sequence[str] | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_permissions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("permission_code", sa.String(100), nullable=False),
        sa.Column("granted_by", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "permission_code", name="uq_user_permissions"),
        schema="identity",
    )
    op.create_index("ix_user_permissions_user", "user_permissions", ["user_id"], schema="identity")


def downgrade() -> None:
    op.drop_table("user_permissions", schema="identity")

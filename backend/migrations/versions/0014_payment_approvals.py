"""payment approvals — single-level approval of collected payments (T-02).

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_approvals",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("due_id", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("collected_by", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("approved_by", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payment_approvals_amount_positive"),
        sa.CheckConstraint("status in ('pending','approved','rejected')", name="ck_payment_approvals_status"),
        sa.CheckConstraint("currency = 'EGP'", name="ck_payment_approvals_currency_egp"),
        schema="sales",
    )
    op.create_index("ix_payment_approvals_status", "payment_approvals", ["status"], schema="sales")


def downgrade() -> None:
    op.drop_index("ix_payment_approvals_status", table_name="payment_approvals", schema="sales")
    op.drop_table("payment_approvals", schema="sales")

"""sales schema — credit tiers, overrides, dues, escalation events.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS sales")

    op.create_table(
        "customer_credit_tiers",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("tier", sa.String(10), nullable=False, server_default=sa.text("'white'")),
        sa.Column("score", sa.Numeric(6, 2), nullable=True),
        sa.Column("credit_limit", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("deferred_pct", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("last_recomputed_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.UniqueConstraint("customer_id", name="uq_credit_tiers_customer"),
        sa.CheckConstraint("tier in ('white','green','yellow','red')", name="ck_credit_tiers_tier"),
        sa.CheckConstraint("currency = 'EGP'", name="ck_credit_tiers_currency_egp"),
        schema="sales",
    )

    op.create_table(
        "credit_overrides",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("credit_limit", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("set_by", sa.BigInteger(), sa.ForeignKey("identity.users.id")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.CheckConstraint("currency = 'EGP'", name="ck_credit_overrides_currency_egp"),
        schema="sales",
    )
    op.create_index("ix_credit_overrides_customer", "credit_overrides", ["customer_id"], schema="sales")

    op.create_table(
        "customer_dues",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("days_late", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default=sa.text("'open'")),
        *_ts(),
        sa.CheckConstraint("amount > 0", name="ck_customer_dues_amount_positive"),
        sa.CheckConstraint("status in ('open','paid','defaulted')", name="ck_customer_dues_status"),
        sa.CheckConstraint("currency = 'EGP'", name="ck_customer_dues_currency_egp"),
        schema="sales",
    )
    op.create_index("ix_customer_dues_customer", "customer_dues", ["customer_id", "status"], schema="sales")

    op.create_table(
        "escalation_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("trigger_reason", sa.String(500), nullable=False),
        sa.Column("is_automatic", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("actor_user_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("level between 1 and 5", name="ck_escalation_level"),
        schema="sales",
    )
    op.create_index("ix_escalation_customer", "escalation_events", ["customer_id", "level"], schema="sales")


def downgrade() -> None:
    op.drop_index("ix_escalation_customer", table_name="escalation_events", schema="sales")
    op.drop_table("escalation_events", schema="sales")
    op.drop_index("ix_customer_dues_customer", table_name="customer_dues", schema="sales")
    op.drop_table("customer_dues", schema="sales")
    op.drop_index("ix_credit_overrides_customer", table_name="credit_overrides", schema="sales")
    op.drop_table("credit_overrides", schema="sales")
    op.drop_table("customer_credit_tiers", schema="sales")
    op.execute("DROP SCHEMA IF EXISTS sales")

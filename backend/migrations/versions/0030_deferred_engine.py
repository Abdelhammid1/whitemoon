"""Flexible deferred-pricing engine (T-28).

Adds the configurable annual-rate engine: a single-row setting, optional
per-tier rates, per-customer exceptions, and snapshot columns on
accounting.deferred_terms so an order keeps the rate/days/fee it was priced at.
All additive; the snapshot columns are nullable (older orders have none).

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: str | Sequence[str] | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deferred_settings",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("annual_pct_general", sa.Numeric(5, 2), nullable=False),
        sa.Column("default_days", sa.Integer(), nullable=False),
        sa.Column("max_days", sa.Integer(), nullable=False),
        sa.Column("allowed_days", sa.JSON(), nullable=False),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reviewed_by", sa.BigInteger(), sa.ForeignKey("identity.users.id")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_deferred_settings_singleton"),
        sa.CheckConstraint("annual_pct_general >= 0", name="ck_deferred_settings_pct_nonneg"),
        sa.CheckConstraint("default_days > 0 and max_days > 0", name="ck_deferred_settings_days_pos"),
        schema="sales",
    )
    op.create_table(
        "deferred_tier_rates",
        sa.Column("tier", sa.String(10), primary_key=True),
        sa.Column("annual_pct", sa.Numeric(5, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("tier in ('white','green','yellow','red')", name="ck_deferred_tier_rates_tier"),
        sa.CheckConstraint("annual_pct is null or annual_pct >= 0", name="ck_deferred_tier_rates_pct"),
        schema="sales",
    )
    op.create_table(
        "deferred_customer_exceptions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("annual_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("set_by", sa.BigInteger(), sa.ForeignKey("identity.users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("customer_id", name="uq_deferred_customer_exceptions"),
        sa.CheckConstraint("annual_pct >= 0", name="ck_deferred_customer_exceptions_pct"),
        schema="sales",
    )
    # Snapshot columns on the per-order deferred terms (nullable for older rows).
    op.add_column("deferred_terms", sa.Column("annual_pct", sa.Numeric(5, 2)), schema="accounting")
    op.add_column("deferred_terms", sa.Column("days", sa.Integer()), schema="accounting")
    op.add_column("deferred_terms", sa.Column("fee", sa.Numeric(18, 4)), schema="accounting")


def downgrade() -> None:
    op.drop_column("deferred_terms", "fee", schema="accounting")
    op.drop_column("deferred_terms", "days", schema="accounting")
    op.drop_column("deferred_terms", "annual_pct", schema="accounting")
    op.drop_table("deferred_customer_exceptions", schema="sales")
    op.drop_table("deferred_tier_rates", schema="sales")
    op.drop_table("deferred_settings", schema="sales")

"""partners schema — terms, deposits, accruals; order→partner attribution.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS partners")

    op.create_table(
        "partner_terms",
        sa.Column("partner_user_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), primary_key=True),
        sa.Column("earns_commission", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("commission_rate_pct", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("earns_investment_return", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("investment_return_rate_pct", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0")),
        *_ts(),
        sa.CheckConstraint(
            "commission_rate_pct >= 0 and commission_rate_pct <= 100",
            name="ck_partner_terms_commission_rate",
        ),
        sa.CheckConstraint(
            "investment_return_rate_pct >= 0 and investment_return_rate_pct <= 100",
            name="ck_partner_terms_return_rate",
        ),
        schema="partners",
    )

    op.create_table(
        "partner_deposits",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("partner_user_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("deposit_date", sa.Date(), nullable=False),
        sa.Column("recovery_conditions", sa.String(2000), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default=sa.text("'held'")),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_reason", sa.String(1000), nullable=True),
        sa.Column("journal_entry_id", sa.BigInteger(), nullable=True),
        sa.Column("refund_journal_entry_id", sa.BigInteger(), nullable=True),
        *_ts(),
        sa.CheckConstraint("amount > 0", name="ck_partner_deposits_amount_positive"),
        sa.CheckConstraint("status in ('held','refunded')", name="ck_partner_deposits_status"),
        sa.CheckConstraint("currency = 'EGP'", name="ck_partner_deposits_currency_egp"),
        schema="partners",
    )
    op.create_index("ix_partner_deposits_partner", "partner_deposits", ["partner_user_id", "status"], schema="partners")

    op.create_table(
        "partner_accruals",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("partner_user_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("basis_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("rate_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("journal_entry_id", sa.BigInteger(), nullable=True),
        *_ts(),
        sa.UniqueConstraint("partner_user_id", "kind", "period_year", "period_month", name="uq_partner_accruals_period"),
        sa.CheckConstraint("kind in ('commission','investment_return')", name="ck_partner_accruals_kind"),
        sa.CheckConstraint("period_month between 1 and 12", name="ck_partner_accruals_month"),
        sa.CheckConstraint("amount >= 0", name="ck_partner_accruals_amount"),
        sa.CheckConstraint("currency = 'EGP'", name="ck_partner_accruals_currency_egp"),
        schema="partners",
    )
    op.create_index("ix_partner_accruals_partner", "partner_accruals", ["partner_user_id", "kind"], schema="partners")

    # Order → partner attribution (the accrual basis).
    op.add_column(
        "orders",
        sa.Column("partner_user_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=True),
        schema="commerce",
    )
    op.create_index("ix_orders_partner", "orders", ["partner_user_id"], schema="commerce")


def downgrade() -> None:
    op.drop_index("ix_orders_partner", table_name="orders", schema="commerce")
    op.drop_column("orders", "partner_user_id", schema="commerce")
    op.drop_index("ix_partner_accruals_partner", table_name="partner_accruals", schema="partners")
    op.drop_table("partner_accruals", schema="partners")
    op.drop_index("ix_partner_deposits_partner", table_name="partner_deposits", schema="partners")
    op.drop_table("partner_deposits", schema="partners")
    op.drop_table("partner_terms", schema="partners")
    op.execute("DROP SCHEMA IF EXISTS partners")

"""partners.partner_ledger — partner current-account movements.

An operational running account (الحساب الجاري) between management and a
channel partner: cash paid to the partner, cash received from them, and manual
adjustments. It does NOT post to the general ledger; the running balance is
computed from the signed movements on read.

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | Sequence[str] | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "partner_ledger",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "partner_user_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("direction", sa.SmallInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column(
            "recorded_by",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_partner_ledger_amount_positive"),
        sa.CheckConstraint("direction in (-1, 1)", name="ck_partner_ledger_direction"),
        sa.CheckConstraint(
            "kind in ('payment_made','payment_received','manual')",
            name="ck_partner_ledger_kind",
        ),
        sa.CheckConstraint("currency = 'EGP'", name="ck_partner_ledger_currency_egp"),
        schema="partners",
    )
    op.create_index(
        "ix_partner_ledger_partner",
        "partner_ledger",
        ["partner_user_id", "id"],
        schema="partners",
    )


def downgrade() -> None:
    op.drop_index("ix_partner_ledger_partner", table_name="partner_ledger", schema="partners")
    op.drop_table("partner_ledger", schema="partners")

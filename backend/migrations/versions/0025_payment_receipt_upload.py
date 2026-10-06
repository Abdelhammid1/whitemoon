"""Customer payment-receipt upload (T-21).

A customer can upload a bank-transfer receipt image; it lands as a *pending*
payment approval for staff to review. Add `source` (collector vs customer) and
`receipt_key` (object-storage key of the uploaded image) to payment_approvals.

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | Sequence[str] | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payment_approvals",
        sa.Column("source", sa.String(length=20), nullable=False, server_default="collector"),
        schema="sales",
    )
    op.add_column(
        "payment_approvals",
        sa.Column("receipt_key", sa.String(length=255), nullable=True),
        schema="sales",
    )
    op.create_check_constraint(
        "ck_payment_approvals_source",
        "payment_approvals",
        "source in ('collector','customer')",
        schema="sales",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_payment_approvals_source", "payment_approvals", schema="sales", type_="check"
    )
    op.drop_column("payment_approvals", "receipt_key", schema="sales")
    op.drop_column("payment_approvals", "source", schema="sales")

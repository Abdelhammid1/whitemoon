"""Allow a 'cancelled' customer due (T-13 order cancellation).

When an order is cancelled its open due is voided; the status CHECK must admit
'cancelled'.

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0024"
down_revision: str | Sequence[str] | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW = "status in ('open','paid','defaulted','cancelled')"
_OLD = "status in ('open','paid','defaulted')"


def upgrade() -> None:
    op.drop_constraint("ck_customer_dues_status", "customer_dues", schema="sales", type_="check")
    op.create_check_constraint("ck_customer_dues_status", "customer_dues", _NEW, schema="sales")


def downgrade() -> None:
    # Fold any cancelled dues into 'paid' (no longer owed) so the old CHECK holds.
    op.execute("UPDATE sales.customer_dues SET status='paid' WHERE status='cancelled'")
    op.drop_constraint("ck_customer_dues_status", "customer_dues", schema="sales", type_="check")
    op.create_check_constraint("ck_customer_dues_status", "customer_dues", _OLD, schema="sales")

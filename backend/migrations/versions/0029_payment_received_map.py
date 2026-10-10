"""Payment-received journal mapping (T-29).

Adds the `payment.received` event → journal map rows so that approving a
customer's uploaded bank-transfer receipt posts a balanced GL entry (debit the
bank 1112, credit the deferred receivable 1132). Data-only, idempotent; the
same rows are also in `app/accounting/seed.py` for fresh DBs and tests.

Revision ID: 0029
Revises: 0028
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0029"
down_revision: str | Sequence[str] | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO accounting.event_journal_map
            (event_type, step, side, account_code, rule_json, amount_source, description,
             created_at, updated_at)
        VALUES
            ('payment.received', 1, 'debit',  '1112', NULL, 'amount',
             'البنك الجاري — تحصيل تحويل العميل', now(), now()),
            ('payment.received', 2, 'credit', '1132', NULL, 'amount',
             'إقفال ذمة العميل الآجلة', now(), now())
        ON CONFLICT ON CONSTRAINT uq_event_journal_map_event_step DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM accounting.event_journal_map WHERE event_type = 'payment.received'")

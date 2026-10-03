"""accounting schema — CoA, periods, journals, event map, deferred terms, receipts.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS accounting")

    # ----- accounting.accounts
    op.create_table(
        "accounts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("name_ar", sa.String(length=200), nullable=False),
        sa.Column("name_en", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column(
            "parent_id",
            sa.BigInteger(),
            sa.ForeignKey("accounting.accounts.id"),
            nullable=True,
        ),
        sa.Column(
            "is_postable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("eta_code", sa.String(length=60), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("code", name="uq_accounts_code"),
        sa.CheckConstraint(
            "type in ('asset','liability','equity','revenue','expense','contra','clearing')",
            name="ck_accounts_type",
        ),
        schema="accounting",
    )

    # ----- accounting.periods
    op.create_table(
        "periods",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column(
            "is_closed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "closed_by",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("year", "month", name="uq_periods_year_month"),
        sa.CheckConstraint("month between 1 and 12", name="ck_periods_month"),
        schema="accounting",
    )

    # ----- accounting.journal_entries
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("entry_no", sa.String(length=40), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column(
            "period_id",
            sa.BigInteger(),
            sa.ForeignKey("accounting.periods.id"),
            nullable=True,
        ),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("source_event_type", sa.String(length=60), nullable=True),
        sa.Column("source_event_id", sa.String(length=60), nullable=True),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column(
            "posted_by",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
        ),
        sa.Column(
            "posted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "reversed_by_entry_id",
            sa.BigInteger(),
            sa.ForeignKey("accounting.journal_entries.id"),
            nullable=True,
        ),
        sa.UniqueConstraint("entry_no", name="uq_journal_entries_entry_no"),
        sa.CheckConstraint(
            "source in ('system','manual')", name="ck_journal_entries_source"
        ),
        schema="accounting",
    )
    op.create_index(
        "ix_journal_entries_date",
        "journal_entries",
        ["entry_date"],
        schema="accounting",
    )

    # ----- accounting.journal_lines
    op.create_table(
        "journal_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "entry_id",
            sa.BigInteger(),
            sa.ForeignKey("accounting.journal_entries.id"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.BigInteger(),
            sa.ForeignKey("accounting.accounts.id"),
            nullable=False,
        ),
        sa.Column(
            "debit", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "credit", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
            server_default=sa.text("'EGP'"),
        ),
        sa.Column("partner_type", sa.String(length=30), nullable=True),
        sa.Column("partner_id", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "(debit > 0 and credit = 0) or (debit = 0 and credit > 0)",
            name="ck_journal_lines_one_side",
        ),
        sa.CheckConstraint("currency = 'EGP'", name="ck_journal_lines_currency_egp"),
        schema="accounting",
    )
    op.create_index(
        "ix_journal_lines_entry", "journal_lines", ["entry_id"], schema="accounting"
    )
    op.create_index(
        "ix_journal_lines_account",
        "journal_lines",
        ["account_id"],
        schema="accounting",
    )

    # ----- accounting.event_journal_map
    op.create_table(
        "event_journal_map",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("side", sa.String(length=6), nullable=False),
        sa.Column("account_code", sa.String(length=10), nullable=True),
        sa.Column("rule_json", sa.JSON(), nullable=True),
        sa.Column("amount_source", sa.String(length=60), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "event_type", "step", name="uq_event_journal_map_event_step"
        ),
        sa.CheckConstraint(
            "side in ('debit','credit')", name="ck_event_journal_map_side"
        ),
        schema="accounting",
    )
    op.create_index(
        "ix_event_journal_map_event_type",
        "event_journal_map",
        ["event_type"],
        schema="accounting",
    )

    # ----- accounting.deferred_terms
    op.create_table(
        "deferred_terms",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("cash_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("deferred_price", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "early_settlement_discount",
            sa.Numeric(18, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("early_settlement_before", sa.Date(), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "discount_applied",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("order_id", name="uq_deferred_terms_order"),
        sa.CheckConstraint(
            "deferred_price >= cash_price", name="ck_deferred_price_gte_cash"
        ),
        sa.CheckConstraint(
            "early_settlement_discount >= 0", name="ck_deferred_discount_nonneg"
        ),
        schema="accounting",
    )

    # ----- accounting.bank_receipts
    op.create_table(
        "bank_receipts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "uploaded_by",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("image_s3_key", sa.String(length=500), nullable=False),
        sa.Column("ocr_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("ocr_reference", sa.String(length=100), nullable=True),
        sa.Column("ocr_raw_json", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("matched_order_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "matched_entry_id",
            sa.BigInteger(),
            sa.ForeignKey("accounting.journal_entries.id"),
            nullable=True,
        ),
        sa.Column("manual_review_reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('pending','matched','manual_review','rejected')",
            name="ck_bank_receipts_status",
        ),
        schema="accounting",
    )

    # ================================================================
    # Triggers — the two financial-integrity rails
    # ================================================================

    # 1) Balance trigger: enforce SUM(debit) = SUM(credit) per entry at
    #    statement end (deferred). Runs on INSERT/UPDATE/DELETE of lines.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION accounting.enforce_entry_balance()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_entry_id BIGINT;
            v_sum NUMERIC(18,4);
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                v_entry_id := OLD.entry_id;
            ELSE
                v_entry_id := NEW.entry_id;
            END IF;

            SELECT COALESCE(SUM(debit) - SUM(credit), 0)
              INTO v_sum
              FROM accounting.journal_lines
             WHERE entry_id = v_entry_id;

            IF v_sum <> 0 THEN
                RAISE EXCEPTION
                    'journal_entry % is unbalanced by %', v_entry_id, v_sum
                    USING ERRCODE = 'check_violation';
            END IF;

            RETURN NULL;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_journal_lines_balance
            AFTER INSERT OR UPDATE OR DELETE
            ON accounting.journal_lines
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW
            EXECUTE FUNCTION accounting.enforce_entry_balance();
        """
    )

    # 2) Period-close guard: block posting into a closed period unless the
    #    session has set `app.allow_closed_period = 'yes'`, which only the
    #    high-privilege manual-journal path does.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION accounting.guard_closed_period()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_entry_date DATE;
            v_closed BOOLEAN;
            v_allow TEXT;
        BEGIN
            SELECT entry_date INTO v_entry_date
              FROM accounting.journal_entries
             WHERE id = NEW.entry_id;

            SELECT is_closed INTO v_closed
              FROM accounting.periods
             WHERE v_entry_date BETWEEN starts_on AND ends_on
             LIMIT 1;

            IF v_closed IS TRUE THEN
                BEGIN
                    v_allow := current_setting('app.allow_closed_period', true);
                EXCEPTION WHEN OTHERS THEN
                    v_allow := NULL;
                END;
                IF v_allow IS DISTINCT FROM 'yes' THEN
                    RAISE EXCEPTION
                        'period containing % is closed; manual override required',
                        v_entry_date
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_journal_lines_period_guard
            BEFORE INSERT OR UPDATE
            ON accounting.journal_lines
            FOR EACH ROW
            EXECUTE FUNCTION accounting.guard_closed_period();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_journal_lines_period_guard ON accounting.journal_lines")
    op.execute("DROP FUNCTION IF EXISTS accounting.guard_closed_period()")
    op.execute("DROP TRIGGER IF EXISTS trg_journal_lines_balance ON accounting.journal_lines")
    op.execute("DROP FUNCTION IF EXISTS accounting.enforce_entry_balance()")

    op.drop_table("bank_receipts", schema="accounting")
    op.drop_table("deferred_terms", schema="accounting")
    op.drop_index(
        "ix_event_journal_map_event_type",
        table_name="event_journal_map",
        schema="accounting",
    )
    op.drop_table("event_journal_map", schema="accounting")
    op.drop_index(
        "ix_journal_lines_account",
        table_name="journal_lines",
        schema="accounting",
    )
    op.drop_index(
        "ix_journal_lines_entry", table_name="journal_lines", schema="accounting"
    )
    op.drop_table("journal_lines", schema="accounting")
    op.drop_index(
        "ix_journal_entries_date",
        table_name="journal_entries",
        schema="accounting",
    )
    op.drop_table("journal_entries", schema="accounting")
    op.drop_table("periods", schema="accounting")
    op.drop_table("accounts", schema="accounting")

    op.execute("DROP SCHEMA IF EXISTS accounting")

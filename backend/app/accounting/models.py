"""Accounting domain — mirrors docs/02-chart-of-accounts.md + docs/03-journal-map.md.

Design rules enforced here:
- Every monetary column is NUMERIC(18,4) + `currency CHECK = 'EGP'`.
- `journal_lines`: exactly one of debit/credit non-zero (CHECK).
- `journal_entries`: SUM(debit) = SUM(credit) — enforced by a Postgres
  trigger created in the migration.
- `event_journal_map` is the single source of truth for which accounts a
  given event posts to; routes never hard-code account codes.
- `periods`: once `is_closed = true`, inserts/updates on `journal_lines`
  with an `entry_date` inside the period are rejected by trigger — the
  override requires setting a session variable only the high-privilege
  manual-journal endpoint sets.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..common.base_model import Base, TimestampMixin

# ---------------------------------------------------------------- Accounts


ACCOUNT_TYPES = ("asset", "liability", "equity", "revenue", "expense", "contra", "clearing")


class Account(Base, TimestampMixin):
    """Chart of Accounts entry. See docs/02-chart-of-accounts.md."""

    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("code", name="uq_accounts_code"),
        CheckConstraint(
            "type in ('asset','liability','equity','revenue','expense','contra','clearing')",
            name="ck_accounts_type",
        ),
        {"schema": "accounting"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("accounting.accounts.id")
    )
    is_postable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # ETA-ready structure (US-11.1) — filled when the integration is activated.
    eta_code: Mapped[str | None] = mapped_column(String(60))
    # Category restriction (food / clothing / ...), used by the posting
    # engine to pick 5110 vs 5120, 4110 vs 4120, etc.
    category: Mapped[str | None] = mapped_column(String(40))


# ---------------------------------------------------------------- Periods


class Period(Base, TimestampMixin):
    """A monthly accounting period. Closing is a sensitive op (US-3.6)."""

    __tablename__ = "periods"
    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_periods_year_month"),
        CheckConstraint("month between 1 and 12", name="ck_periods_month"),
        {"schema": "accounting"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    year: Mapped[int] = mapped_column(nullable=False)
    month: Mapped[int] = mapped_column(nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    closed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id")
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------- Journal


class JournalEntry(Base):
    """A balanced double-entry journal entry.

    SUM(debit) = SUM(credit) across its lines — enforced by a deferred
    constraint-style trigger created in the migration.
    """

    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint("entry_no", name="uq_journal_entries_entry_no"),
        Index("ix_journal_entries_date", "entry_date"),
        {"schema": "accounting"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    entry_no: Mapped[str] = mapped_column(String(40), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("accounting.periods.id")
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # system | manual
    source_event_type: Mapped[str | None] = mapped_column(String(60))
    source_event_id: Mapped[str | None] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    posted_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id")
    )
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reversed_by_entry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("accounting.journal_entries.id")
    )

    lines: Mapped[list[JournalLine]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JournalLine.id",
    )


class JournalLine(Base):
    """One side of a journal entry. CHECK: exactly one of debit/credit non-zero."""

    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint(
            "(debit > 0 and credit = 0) or (debit = 0 and credit > 0)",
            name="ck_journal_lines_one_side",
        ),
        CheckConstraint("currency = 'EGP'", name="ck_journal_lines_currency_egp"),
        Index("ix_journal_lines_entry", "entry_id"),
        Index("ix_journal_lines_account", "account_id"),
        {"schema": "accounting"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("accounting.journal_entries.id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("accounting.accounts.id"), nullable=False
    )
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    # Analytical dimensions — docs/02 marks several accounts "تحليلي لكل X".
    partner_type: Mapped[str | None] = mapped_column(String(30))  # supplier/customer/agent/branch
    partner_id: Mapped[int | None] = mapped_column(BigInteger)
    description: Mapped[str | None] = mapped_column(String(500))

    entry: Mapped[JournalEntry] = relationship(back_populates="lines")


# ---------------------------------------------------------------- Event → Journal map


class EventJournalMap(Base, TimestampMixin):
    """Business-rule table mirroring docs/03-journal-map.md.

    Each row defines a template line for a given event_type at a given
    `step` ordinal; `rule_json` can describe account selection logic
    (e.g. "pick 5110 if category=food else 5120", or
    "pick 1151/1152/1153/1154 by stock_balances.location_type"). The
    posting engine evaluates these at post time.
    """

    __tablename__ = "event_journal_map"
    __table_args__ = (
        UniqueConstraint("event_type", "step", name="uq_event_journal_map_event_step"),
        {"schema": "accounting"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    step: Mapped[int] = mapped_column(nullable=False)
    side: Mapped[str] = mapped_column(String(6), nullable=False)  # 'debit' | 'credit'
    # Static code, OR null when `rule_json` picks dynamically.
    account_code: Mapped[str | None] = mapped_column(String(10))
    # Expression like {"by_category": {"food":"5110","clothing":"5120"}}
    # or {"by_location": {"supplier":"1151_or_1152","channel_partner":"1153","in_transit":"1154"}}.
    rule_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    amount_source: Mapped[str] = mapped_column(String(60), nullable=False)
    # 'amount', 'cost', 'cash_price', 'deferred_price', 'spread', 'discount', …
    description: Mapped[str] = mapped_column(String(300), nullable=False)


# ---------------------------------------------------------------- Deferred terms (US-3.4)


class DeferredTerm(Base, TimestampMixin):
    """Shariah-compliant deferred-pricing record for a single order.

    - `cash_price` + `deferred_price` are both locked at order creation.
    - `early_settlement_discount` is a FIXED discount, not a daily accrual.
    - `early_settlement_before` is the cut-off date for the discount.
    """

    __tablename__ = "deferred_terms"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_deferred_terms_order"),
        CheckConstraint("deferred_price >= cash_price", name="ck_deferred_price_gte_cash"),
        CheckConstraint(
            "early_settlement_discount >= 0", name="ck_deferred_discount_nonneg"
        ),
        {"schema": "accounting"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cash_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    deferred_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    early_settlement_discount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    early_settlement_before: Mapped[date | None] = mapped_column(Date)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discount_applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # T-28 snapshot: the annual rate %, duration in days, and computed fee this
    # order was priced at — so a later rate change never alters a placed order.
    # Nullable: orders placed before T-28 have no snapshot.
    annual_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    days: Mapped[int | None] = mapped_column(Integer)
    fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))


# ---------------------------------------------------------------- Bank receipts (US-3.3)


class BankReceipt(Base, TimestampMixin):
    """Scanned bank-transfer receipt pending OCR match."""

    __tablename__ = "bank_receipts"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending','matched','manual_review','rejected')",
            name="ck_bank_receipts_status",
        ),
        {"schema": "accounting"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uploaded_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    image_s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    ocr_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    ocr_reference: Mapped[str | None] = mapped_column(String(100))
    ocr_raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    matched_order_id: Mapped[int | None] = mapped_column(BigInteger)
    matched_entry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("accounting.journal_entries.id")
    )
    manual_review_reason: Mapped[str | None] = mapped_column(String(500))

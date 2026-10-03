"""Channel-partner financials — EPIC 6 (deposits, terms, accruals).

Schema `partners`. The partner identity (agent vs branch, display name, geo
scope) lives on `identity.channel_partner_profiles`; this schema holds the
money: the recoverable deposit (US-6.1), the entitlement terms, and the
monthly commission / investment-return accruals (US-6.2).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
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
)
from sqlalchemy.orm import Mapped, mapped_column

from ..common.base_model import Base, TimestampMixin

ACCRUAL_KINDS = ("commission", "investment_return")
DEPOSIT_STATUSES = ("held", "refunded")


class PartnerTerms(Base, TimestampMixin):
    """What a partner is entitled to. Branches earn neither commission nor
    investment return (US-6.3); agents may earn either or both."""

    __tablename__ = "partner_terms"
    __table_args__ = (
        CheckConstraint(
            "commission_rate_pct >= 0 and commission_rate_pct <= 100",
            name="ck_partner_terms_commission_rate",
        ),
        CheckConstraint(
            "investment_return_rate_pct >= 0 and investment_return_rate_pct <= 100",
            name="ck_partner_terms_return_rate",
        ),
        {"schema": "partners"},
    )

    partner_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), primary_key=True
    )
    earns_commission: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    commission_rate_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )
    earns_investment_return: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    investment_return_rate_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )


class PartnerDeposit(Base, TimestampMixin):
    """A financial deposit (تأمين) held by the company as a recoverable
    liability (US-6.1). Posting hits 2120 (Agent Deposits)."""

    __tablename__ = "partner_deposits"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_partner_deposits_amount_positive"),
        CheckConstraint("status in ('held','refunded')", name="ck_partner_deposits_status"),
        CheckConstraint("currency = 'EGP'", name="ck_partner_deposits_currency_egp"),
        Index("ix_partner_deposits_partner", "partner_user_id", "status"),
        {"schema": "partners"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    partner_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    deposit_date: Mapped[date] = mapped_column(Date, nullable=False)
    recovery_conditions: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="held")
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refund_reason: Mapped[str | None] = mapped_column(String(1000))
    journal_entry_id: Mapped[int | None] = mapped_column(BigInteger)
    refund_journal_entry_id: Mapped[int | None] = mapped_column(BigInteger)


class PartnerAccrual(Base, TimestampMixin):
    """A monthly commission or investment-return accrual (US-6.2), computed
    server-side from realized sales in the partner's scope. One row per
    (partner, kind, year, month)."""

    __tablename__ = "partner_accruals"
    __table_args__ = (
        UniqueConstraint(
            "partner_user_id",
            "kind",
            "period_year",
            "period_month",
            name="uq_partner_accruals_period",
        ),
        CheckConstraint(
            "kind in ('commission','investment_return')", name="ck_partner_accruals_kind"
        ),
        CheckConstraint(
            "period_month between 1 and 12", name="ck_partner_accruals_month"
        ),
        CheckConstraint("amount >= 0", name="ck_partner_accruals_amount"),
        CheckConstraint("currency = 'EGP'", name="ck_partner_accruals_currency_egp"),
        Index("ix_partner_accruals_partner", "partner_user_id", "kind"),
        {"schema": "partners"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    partner_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    basis_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    journal_entry_id: Mapped[int | None] = mapped_column(BigInteger)

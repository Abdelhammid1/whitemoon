"""Sales & Customers — EPIC 5 (credit tiers, limits, dunning).

Implements docs/04-credit-rating-rules.md:
- 4-colour tier (white / green / yellow / red), auto-computed from the
  customer's payment history (US-5.1).
- Default credit limit per tier, overridable with a reason (US-5.2).
- 5-level escalation; levels 1–4 automatic, level 5 manual-only (US-5.3).
Dues feed the algorithm; a deferred order creates a due with a due date.
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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..common.base_model import Base, TimestampMixin

TIERS = ("white", "green", "yellow", "red")
DUE_STATUSES = ("open", "paid", "defaulted")


class CustomerCreditTier(Base, TimestampMixin):
    __tablename__ = "customer_credit_tiers"
    __table_args__ = (
        UniqueConstraint("customer_id", name="uq_credit_tiers_customer"),
        CheckConstraint("tier in ('white','green','yellow','red')", name="ck_credit_tiers_tier"),
        CheckConstraint("currency = 'EGP'", name="ck_credit_tiers_currency_egp"),
        {"schema": "sales"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    tier: Mapped[str] = mapped_column(String(10), nullable=False, default="white")
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    deferred_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    last_recomputed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Escalation floor (docs/04 §2): the worst colour an active dunning
    # escalation has forced the customer to. recompute() never shows a tier
    # better (less toward red) than this until de-escalation recovers it a step
    # at a time. NULL = no active floor. floor_set_at gates the 24h recovery.
    escalation_floor: Mapped[str | None] = mapped_column(String(10))
    floor_set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CreditTierSetting(Base, TimestampMixin):
    """Admin-configurable default limit + deferred % per colour tier (T-11).

    Seeded from the signed defaults; editable from the UI so a limit change
    doesn't need a code deploy. `credit.py` reads this, falling back to the
    coded defaults when a row is missing."""

    __tablename__ = "credit_tier_settings"
    __table_args__ = (
        CheckConstraint("tier in ('white','green','yellow','red')", name="ck_tier_settings_tier"),
        CheckConstraint("currency = 'EGP'", name="ck_tier_settings_currency_egp"),
        {"schema": "sales"},
    )

    tier: Mapped[str] = mapped_column(String(10), primary_key=True)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    deferred_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )


class CreditOverride(Base, TimestampMixin):
    """Manual credit-limit exception (US-5.2) — reason + actor always logged."""

    __tablename__ = "credit_overrides"
    __table_args__ = (
        CheckConstraint("currency = 'EGP'", name="ck_credit_overrides_currency_egp"),
        Index("ix_credit_overrides_customer", "customer_id"),
        {"schema": "sales"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    set_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("identity.users.id"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CustomerDue(Base, TimestampMixin):
    """A receivable with a due date — the input to the credit algorithm."""

    __tablename__ = "customer_dues"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_customer_dues_amount_positive"),
        CheckConstraint(
            "status in ('open','paid','defaulted','cancelled')", name="ck_customer_dues_status"
        ),
        CheckConstraint("currency = 'EGP'", name="ck_customer_dues_currency_egp"),
        Index("ix_customer_dues_customer", "customer_id", "status"),
        {"schema": "sales"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    order_id: Mapped[int | None] = mapped_column(BigInteger)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_date: Mapped[date | None] = mapped_column(Date)
    days_late: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="open")


class PaymentApproval(Base, TimestampMixin):
    """A customer payment collected by an agent/branch that needs exactly one
    approval (the branch/agent manager) before it is applied — no intermediate
    level (US-3.2b, T-02). The collector may not approve their own."""

    __tablename__ = "payment_approvals"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_approvals_amount_positive"),
        CheckConstraint(
            "status in ('pending','approved','rejected')", name="ck_payment_approvals_status"
        ),
        CheckConstraint("currency = 'EGP'", name="ck_payment_approvals_currency_egp"),
        Index("ix_payment_approvals_status", "status"),
        {"schema": "sales"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    due_id: Mapped[int | None] = mapped_column(BigInteger)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EGP", server_default="EGP"
    )
    paid_on: Mapped[date] = mapped_column(Date, nullable=False)
    collected_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="pending")
    approved_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(String(1000))


class EscalationEvent(Base):
    """A dunning step (US-5.3). Levels 1–4 are automatic; level 5 is manual
    and carries the acting admin's id."""

    __tablename__ = "escalation_events"
    __table_args__ = (
        CheckConstraint("level between 1 and 5", name="ck_escalation_level"),
        Index("ix_escalation_customer", "customer_id", "level"),
        {"schema": "sales"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    is_automatic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id")
    )
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

"""Credit tiers, limits, and dues — EPIC 5 (docs/04-credit-rating-rules.md).

The thresholds, weights, and default limits below mirror the signed credit
rules. They are a business rule (like the Chart of Accounts) — changes must
be re-approved, not adjusted ad hoc.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select, text

from ...common.errors import BadRequest, Forbidden, NotFound
from ...common.money import to_money
from ...extensions import db
from ...identity.models import User
from ..models import CreditOverride, CustomerCreditTier, CustomerDue

# tier -> (default credit limit EGP, deferred % allowed)
TIER_LIMITS: dict[str, tuple[Decimal, Decimal]] = {
    "green": (Decimal("500000"), Decimal("100")),
    "white": (Decimal("250000"), Decimal("60")),
    "yellow": (Decimal("100000"), Decimal("40")),
    "red": (Decimal("0"), Decimal("0")),
}

WINDOW_DAYS = 365
MIN_HISTORY = 3
NEW_ACCOUNT_DAYS = 90
GREEN_SCORE = Decimal("85")
YELLOW_SCORE = Decimal("50")

# Dues are judged against the business calendar day (Egypt), not UTC — a
# client at UTC+2 sending "today" must not be rejected as a future date.
BUSINESS_TZ = ZoneInfo("Africa/Cairo")

# Namespace for the per-customer advisory lock that serialises concurrent
# deferred checkouts (prevents a limit-check TOCTOU). Any stable int works.
_CREDIT_LOCK_NS = 0x4352  # "CR"


def _lock_customer(customer_id: int) -> None:
    """Take a transaction-scoped advisory lock on this customer's credit.

    Held until the surrounding transaction commits/rolls back, so two
    concurrent deferred orders for the same customer are serialised: the
    second blocks until the first's due is committed and visible.
    """
    db.session.execute(
        text("SELECT pg_advisory_xact_lock(:ns, :cid)"),
        {"ns": _CREDIT_LOCK_NS, "cid": customer_id},
    )


@dataclass(frozen=True)
class Classification:
    tier: str
    score: Decimal | None


def _today() -> date:
    return datetime.now(UTC).date()


def _dues_in_window(customer_id: int) -> list[CustomerDue]:
    cutoff = _today() - timedelta(days=WINDOW_DAYS)
    stmt = select(CustomerDue).where(
        CustomerDue.customer_id == customer_id, CustomerDue.due_date >= cutoff
    )
    return list(db.session.execute(stmt).scalars().all())


def classify(customer_id: int) -> Classification:
    user = db.session.get(User, customer_id)
    if user is None:
        raise NotFound("Customer not found", code="customer_not_found")

    dues = _dues_in_window(customer_id)
    settled = [d for d in dues if d.status in ("paid", "defaulted")]
    open_dues = [d for d in dues if d.status == "open"]
    today = _today()

    account_age = (
        (today - user.created_at.date()).days if user.created_at else NEW_ACCOUNT_DAYS
    )
    oldest_open_days = max(((today - d.due_date).days for d in open_dues), default=0)

    # White: brand-new or too little history to score.
    if len(settled) < MIN_HISTORY or account_age < NEW_ACCOUNT_DAYS:
        return Classification(tier="white", score=None)

    total = len(settled)
    on_time = sum(1 for d in settled if (d.days_late or 0) <= 0)
    late_1_7 = sum(1 for d in settled if 1 <= (d.days_late or 0) <= 7)
    late_8_30 = sum(1 for d in settled if 8 <= (d.days_late or 0) <= 30)
    late_31_60 = sum(1 for d in settled if 31 <= (d.days_late or 0) <= 60)
    late_61_plus = sum(1 for d in settled if (d.days_late or 0) > 60)
    defaults = sum(1 for d in settled if d.status == "defaulted")

    on_time_ratio = Decimal(on_time) / Decimal(total)
    weighted_late = (
        Decimal(late_1_7) * 1
        + Decimal(late_8_30) * 3
        + Decimal(late_31_60) * 6
        + Decimal(late_61_plus) * 10
        + Decimal(defaults) * 20
    ) / Decimal(total)
    score = (Decimal("100") * on_time_ratio - Decimal("100") * weighted_late / 10).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )
    if score < 0:
        score = Decimal("0")
    if score > 100:
        score = Decimal("100")

    # Strictest condition wins.
    if score < YELLOW_SCORE or oldest_open_days > 60 or defaults >= 1:
        tier = "red"
    elif score >= GREEN_SCORE and oldest_open_days <= 30:
        tier = "green"
    else:
        tier = "yellow"
    return Classification(tier=tier, score=score)


def recompute(customer_id: int) -> CustomerCreditTier:
    c = classify(customer_id)
    limit, pct = TIER_LIMITS[c.tier]
    row = db.session.execute(
        select(CustomerCreditTier).where(CustomerCreditTier.customer_id == customer_id)
    ).scalar_one_or_none()
    if row is None:
        row = CustomerCreditTier(customer_id=customer_id)
        db.session.add(row)
    row.tier = c.tier
    row.score = c.score
    row.credit_limit = limit
    row.deferred_pct = pct
    row.last_recomputed_at = datetime.now(UTC)
    db.session.flush()
    return row


def get_tier(customer_id: int) -> CustomerCreditTier:
    row = db.session.execute(
        select(CustomerCreditTier).where(CustomerCreditTier.customer_id == customer_id)
    ).scalar_one_or_none()
    return row if row is not None else recompute(customer_id)


def active_override(customer_id: int) -> CreditOverride | None:
    now = datetime.now(UTC)
    stmt = (
        select(CreditOverride)
        .where(
            CreditOverride.customer_id == customer_id,
            CreditOverride.revoked_at.is_(None),
        )
        .order_by(CreditOverride.id.desc())
    )
    for ov in db.session.execute(stmt).scalars():
        if ov.expires_at is None or ov.expires_at > now:
            return ov
    return None


def effective_limit(customer_id: int) -> Decimal:
    ov = active_override(customer_id)
    if ov is not None:
        return to_money(ov.credit_limit)
    return to_money(get_tier(customer_id).credit_limit)


def outstanding(customer_id: int) -> Decimal:
    rows = db.session.execute(
        select(CustomerDue.amount).where(
            CustomerDue.customer_id == customer_id, CustomerDue.status == "open"
        )
    ).scalars().all()
    return sum((to_money(a) for a in rows), start=Decimal("0"))


def check_credit(*, customer_id: int, order_amount: Decimal, deferred: bool) -> None:
    """Enforce the credit limit on a new deferred order (US-5.2). Red tier
    cannot defer.

    Cash orders consume no credit and skip the check. For a deferred order we
    first serialise on the customer (advisory lock) and recompute the tier so
    the decision uses the customer's *current* standing, never a stale cached
    tier — both the lock and the recompute must happen inside the caller's
    checkout transaction, which holds the lock through to COMMIT.
    """
    if not deferred:
        return
    _lock_customer(customer_id)
    tier = recompute(customer_id)
    if tier.tier == "red":
        raise Forbidden("التصنيف الأحمر لا يسمح بالبيع الآجل — نقدي فقط", code="deferred_blocked_red")
    new_exposure = outstanding(customer_id) + to_money(order_amount)
    limit = effective_limit(customer_id)
    if new_exposure > limit:
        raise Forbidden(
            f"تجاوز السقف الائتماني ({limit} ج.م)", code="credit_limit_exceeded"
        )


def record_due(*, customer_id: int, order_id: int | None, amount: Decimal, due_date: date) -> CustomerDue:
    due = CustomerDue(
        customer_id=customer_id,
        order_id=order_id,
        amount=to_money(amount),
        due_date=due_date,
        status="open",
    )
    db.session.add(due)
    db.session.flush()
    return due


def record_payment(*, due_id: int, paid_on: date) -> CustomerDue:
    due = db.session.get(CustomerDue, due_id)
    if due is None:
        raise NotFound("Due not found", code="due_not_found")
    if due.status != "open":
        raise BadRequest("الذمة ليست مفتوحة", code="due_not_open")
    if paid_on > datetime.now(BUSINESS_TZ).date():
        raise BadRequest("تاريخ السداد لا يمكن أن يكون في المستقبل", code="paid_on_future")
    days_late = (paid_on - due.due_date).days
    due.paid_date = paid_on
    due.days_late = days_late
    due.status = "defaulted" if days_late > 90 else "paid"
    db.session.flush()
    recompute(due.customer_id)
    db.session.commit()
    return due


def set_override(*, customer_id: int, credit_limit: Decimal, reason: str, set_by: int) -> CreditOverride:
    if len(reason.strip()) < 5:
        raise BadRequest("السبب إلزامي (٥ أحرف فأكثر)", code="reason_required")
    ov = CreditOverride(
        customer_id=customer_id,
        credit_limit=to_money(credit_limit),
        reason=reason.strip(),
        set_by=set_by,
    )
    db.session.add(ov)
    db.session.commit()
    return ov


def serialize_tier(customer_id: int) -> dict[str, Any]:
    tier = get_tier(customer_id)
    return {
        "customer_id": customer_id,
        "tier": tier.tier,
        "score": str(tier.score) if tier.score is not None else None,
        "credit_limit_default": str(tier.credit_limit),
        "effective_limit": str(effective_limit(customer_id)),
        "deferred_pct": str(tier.deferred_pct),
        "outstanding": str(outstanding(customer_id)),
    }

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

from sqlalchemy import func, select, text

from ...common.errors import BadRequest, Forbidden, NotFound
from ...common.money import to_money
from ...extensions import db
from ...identity.models import CustomerProfile, User
from ..models import CreditOverride, CreditTierSetting, CustomerCreditTier, CustomerDue

# tier -> (default credit limit EGP, deferred % allowed). These are the coded
# fallback; the live values come from `sales.credit_tier_settings` (T-11) and
# are editable from the admin UI without a deploy.
TIER_LIMITS: dict[str, tuple[Decimal, Decimal]] = {
    "green": (Decimal("500000"), Decimal("100")),
    "white": (Decimal("250000"), Decimal("60")),
    "yellow": (Decimal("100000"), Decimal("40")),
    "red": (Decimal("0"), Decimal("0")),
}


def tier_defaults(tier: str) -> tuple[Decimal, Decimal]:
    """Live limit + deferred % for a tier: the DB setting if present, else the
    coded fallback (so a fresh DB / tests still work)."""
    row = db.session.get(CreditTierSetting, tier)
    if row is not None:
        return to_money(row.credit_limit), to_money(row.deferred_pct)
    return TIER_LIMITS[tier]


def seed_tier_settings() -> None:
    """Insert the signed defaults for any tier not yet configured."""
    for tier, (limit, pct) in TIER_LIMITS.items():
        if db.session.get(CreditTierSetting, tier) is None:
            db.session.add(CreditTierSetting(tier=tier, credit_limit=limit, deferred_pct=pct))
    db.session.flush()


def set_tier_setting(*, tier: str, credit_limit: Decimal, deferred_pct: Decimal) -> CreditTierSetting:
    if tier not in TIER_LIMITS:
        raise BadRequest("تصنيف غير صالح", code="bad_tier")
    row = db.session.get(CreditTierSetting, tier)
    if row is None:
        row = CreditTierSetting(tier=tier, credit_limit=to_money(credit_limit), deferred_pct=to_money(deferred_pct))
        db.session.add(row)
    else:
        row.credit_limit = to_money(credit_limit)
        row.deferred_pct = to_money(deferred_pct)
    db.session.commit()
    return row


def all_tier_settings() -> list[dict[str, Any]]:
    out = []
    for tier in ("green", "white", "yellow", "red"):
        limit, pct = tier_defaults(tier)
        out.append({"tier": tier, "credit_limit": str(limit), "deferred_pct": str(pct)})
    return out

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
    # UTC calendar day — the single date source for the credit module
    # (classify, overdue, escalation). The Beat scan runs daily regardless;
    # the ≤3h UTC/Cairo boundary offset is immaterial to range-based day bands.
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


# Colour severity toward red (higher = worse). `white` (new account, 250k)
# sits between green and yellow by limit.
_SEVERITY = {"green": 0, "white": 1, "yellow": 2, "red": 3}
# One-step forced downgrade toward red (docs/04 §2 L3): green/white → yellow,
# yellow → red; red is terminal.
_DOWNGRADE = {"green": "yellow", "white": "yellow", "yellow": "red", "red": "red"}
# One-step de-escalation recovery toward green: red → yellow; yellow (or better)
# is released so the score decides white/green ("أحمر → أصفر → أبيض/أخضر").
_RECOVER = {"red": "yellow"}
DEESCALATE_AFTER_HOURS = 24


def _severity(tier: str) -> int:
    return _SEVERITY.get(tier, 0)


def recompute(customer_id: int) -> CustomerCreditTier:
    c = classify(customer_id)
    row = db.session.execute(
        select(CustomerCreditTier).where(CustomerCreditTier.customer_id == customer_id)
    ).scalar_one_or_none()
    if row is None:
        row = CustomerCreditTier(customer_id=customer_id)
        db.session.add(row)
    # An active escalation floor never lets the shown tier be better (less
    # toward red) than the floor (docs/04 §2).
    effective = c.tier
    if row.escalation_floor and _severity(row.escalation_floor) > _severity(c.tier):
        effective = row.escalation_floor
    limit, pct = tier_defaults(effective)
    row.tier = effective
    row.score = c.score
    row.credit_limit = limit
    row.deferred_pct = pct
    row.last_recomputed_at = datetime.now(UTC)
    db.session.flush()
    return row


def apply_l3_downgrade(customer_id: int) -> CustomerCreditTier:
    """Force the colour tier one step toward red (docs/04 §2, Level 3). Sets or
    worsens the escalation floor so it persists through recompute until
    de-escalation recovers it. Idempotent at red."""
    row = get_tier(customer_id)
    target = _DOWNGRADE.get(row.tier, row.tier)
    if _severity(target) <= _severity(row.tier):
        return row  # already at red — nothing to downgrade
    if not row.escalation_floor or _severity(target) > _severity(row.escalation_floor):
        row.escalation_floor = target
        row.floor_set_at = datetime.now(UTC)
        db.session.flush()
    return recompute(customer_id)


def de_escalate(customer_id: int) -> bool:
    """Recover the escalation floor one step toward green — but only once the
    customer has no overdue open dues and ≥24h have passed since the floor last
    moved (docs/04 §2). Returns True if a step was recovered."""
    row = db.session.execute(
        select(CustomerCreditTier).where(CustomerCreditTier.customer_id == customer_id)
    ).scalar_one_or_none()
    if row is None or not row.escalation_floor:
        return False
    today = _today()
    if any((today - d.due_date).days > 0 for d in _open_dues(customer_id)):
        return False  # still delinquent — no recovery
    if row.floor_set_at and (
        datetime.now(UTC) - row.floor_set_at
    ) < timedelta(hours=DEESCALATE_AFTER_HOURS):
        return False
    recovered = _RECOVER.get(row.escalation_floor)
    if recovered is None:
        row.escalation_floor = None  # released — the score decides the tier
        row.floor_set_at = None
    else:
        row.escalation_floor = recovered
        row.floor_set_at = datetime.now(UTC)
    db.session.flush()
    recompute(customer_id)
    return True


def de_escalate_all() -> int:
    """Run one de-escalation step for every customer with an active floor
    (nightly). Returns the number of customers that recovered a step."""
    ids = list(
        db.session.execute(
            select(CustomerCreditTier.customer_id).where(
                CustomerCreditTier.escalation_floor.isnot(None)
            )
        ).scalars()
    )
    n = sum(1 for cid in ids if de_escalate(cid))
    db.session.commit()
    return n


def recompute_all_active() -> int:
    """Recompute the credit tier for every active customer (the nightly job).
    Returns the number recomputed. Commits once at the end."""
    ids = list(
        db.session.execute(
            select(User.id).where(User.kind == "customer", User.status == "active")
        ).scalars()
    )
    for cid in ids:
        recompute(cid)
    db.session.commit()
    return len(ids)


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


# docs/04 §2 — order-blocking escalation thresholds (days overdue on open dues).
ESC_L2_MIN_DAYS = 8  # L2 trigger: a due ≥8 days overdue (cumulative to L4)
ESC_L4_MIN_DAYS = 31  # L4 trigger: ≥31 days → reject all new orders until settled
ESC_TWO_DUES_MIN_DAYS = 7  # two open dues ≥ 7 days overdue → L2
ESC_LIMIT_CUT = Decimal("0.50")  # L2 halves the effective limit


def _open_dues(customer_id: int) -> list[CustomerDue]:
    return list(
        db.session.execute(
            select(CustomerDue).where(
                CustomerDue.customer_id == customer_id, CustomerDue.status == "open"
            )
        ).scalars().all()
    )


def order_block_level(customer_id: int) -> int:
    """How far the customer's *current* overdue standing blocks new orders,
    computed from live open dues (not recorded escalation events) so it clears
    automatically once the dues are settled:

      4 → reject all new orders (cash or deferred) until settled  [≥31 days]
      2 → block new deferred + 50% limit cut  [a due ≥8 days overdue, or two
          dues ≥7 days overdue]
      0 → no block.

    docs/04 §2 puts the L2 actions (cut + deferred block) at 8–15 days and the
    16–30-day band at L3 (a one-step colour downgrade). Until that forced
    downgrade and the daily scan are implemented, the L2 block is applied
    cumulatively from 8 days through 30 — a worsening delinquency never regains
    deferred access it already lost. A manual override (a deliberate admin
    exception) lifts the L2 actions, but never the L4 freeze.
    """
    today = _today()
    overdue_days = [n for n in ((today - d.due_date).days for d in _open_dues(customer_id)) if n > 0]
    if not overdue_days:
        return 0
    if max(overdue_days) >= ESC_L4_MIN_DAYS:
        return 4  # freeze all orders — not lifted by an override
    two_dues = sum(1 for n in overdue_days if n >= ESC_TWO_DUES_MIN_DAYS) >= 2
    if max(overdue_days) >= ESC_L2_MIN_DAYS or two_dues:
        # An active override lifts the L2 auto-actions (but not the L4 freeze).
        return 0 if active_override(customer_id) is not None else 2
    return 0


def effective_limit(customer_id: int) -> Decimal:
    ov = active_override(customer_id)
    if ov is not None:
        # A manual exception is a deliberate admin decision — it wins, and the
        # automatic L2 cut does not apply on top of it.
        return to_money(ov.credit_limit)
    base = to_money(get_tier(customer_id).credit_limit)
    if order_block_level(customer_id) >= 2:
        base = (base * (Decimal("1") - ESC_LIMIT_CUT)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
    return base


def outstanding(customer_id: int) -> Decimal:
    rows = db.session.execute(
        select(CustomerDue.amount).where(
            CustomerDue.customer_id == customer_id, CustomerDue.status == "open"
        )
    ).scalars().all()
    return sum((to_money(a) for a in rows), start=Decimal("0"))


def check_credit(*, customer_id: int, order_amount: Decimal, deferred: bool) -> None:
    """Enforce credit control on a new order (US-5.2, US-5.3 auto-escalation).

    Order-blocking escalation is derived from the customer's *current* overdue
    dues (`order_block_level`), so it lifts automatically on settlement:
      • Level 4 (≥31 days overdue) rejects ALL new orders — cash or deferred —
        until the dues are settled.
      • Level 2 (a due ≥8 days overdue, or two dues ≥7 days) blocks new
        deferred orders and halves the effective limit.
    A red tier can never defer. A manual override lifts the L2 auto-actions
    (it is a deliberate admin exception) but not the L4 freeze.

    For a deferred order we serialise on the customer (advisory lock) and
    recompute the tier so the decision uses current standing — the lock and
    recompute run inside the caller's checkout transaction, held to COMMIT.
    """
    block = order_block_level(customer_id)
    if block >= 4:
        raise Forbidden(
            "طلبات هذا العميل موقوفة حتى تسوية المتأخرات (تصعيد المستوى ٤)",
            code="orders_frozen_overdue",
        )
    if not deferred:
        return
    _lock_customer(customer_id)
    tier = recompute(customer_id)
    if tier.tier == "red":
        raise Forbidden("التصنيف الأحمر لا يسمح بالبيع الآجل — نقدي فقط", code="deferred_blocked_red")
    # order_block_level already returns 0 for a customer with an active override,
    # so this only fires when the L2 block is genuinely in effect.
    if block >= 2:
        raise Forbidden(
            "البيع الآجل موقوف مؤقتًا بسبب تأخر السداد (تصعيد المستوى ٢)",
            code="deferred_blocked_escalation",
        )
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


def open_dues_for_customer(customer_id: int) -> list[dict[str, Any]]:
    """Open dues for the customer's payment-upload selector (T-29): amount, due
    date, order number, and the LIVE days-overdue (not the settled `days_late`,
    which is only written once a due is paid). Oldest due first."""
    from ...commerce.models import Order

    today = _today()
    rows = db.session.execute(
        select(CustomerDue)
        .where(CustomerDue.customer_id == customer_id, CustomerDue.status == "open")
        .order_by(CustomerDue.due_date.asc(), CustomerDue.id.asc())
    ).scalars().all()
    order_ids = {d.order_id for d in rows if d.order_id is not None}
    numbers: dict[int, str] = {}
    if order_ids:
        numbers = {
            oid: num
            for oid, num in db.session.execute(
                select(Order.id, Order.number).where(Order.id.in_(order_ids))
            ).all()
        }
    out: list[dict[str, Any]] = []
    for d in rows:
        overdue = (today - d.due_date).days
        out.append(
            {
                "id": d.id,
                "amount": str(to_money(d.amount)),
                "due_date": d.due_date.isoformat(),
                "order_id": d.order_id,
                "order_number": numbers.get(d.order_id) if d.order_id is not None else None,
                "days_overdue": overdue if overdue > 0 else 0,
            }
        )
    return out


def list_dues(customer_id: int) -> list[CustomerDue]:
    return list(
        db.session.execute(
            select(CustomerDue)
            .where(CustomerDue.customer_id == customer_id)
            .order_by(CustomerDue.due_date.desc(), CustomerDue.id.desc())
        ).scalars().all()
    )


def dunning_list(*, min_days: int = 0, tier: str | None = None) -> list[dict[str, Any]]:
    """Customers with OVERDUE open dues for the collections/dunning board (C4),
    worst overdue first. Read-only: it never recomputes/writes a tier (so a GET
    stays a read) — it uses the stored tier, falling back to a non-persisting
    classification only when none exists."""
    today = _today()
    rows = db.session.execute(
        select(
            CustomerDue.customer_id,
            func.count().label("open_count"),
            func.coalesce(func.sum(CustomerDue.amount), 0).label("outstanding"),
            func.min(CustomerDue.due_date).label("oldest_due"),
        )
        .where(CustomerDue.status == "open")
        .group_by(CustomerDue.customer_id)
    ).all()

    # A dunning board lists the overdue (≥1 day), honouring a higher floor.
    threshold = max(1, min_days)
    candidates = [
        (cid, open_count, outstanding_sum, (today - oldest_due).days)
        for (cid, open_count, outstanding_sum, oldest_due) in rows
        if oldest_due is not None and (today - oldest_due).days >= threshold
    ]
    if not candidates:
        return []

    ids = [c[0] for c in candidates]
    profiles = {
        p.user_id: p
        for p in db.session.execute(
            select(CustomerProfile).where(CustomerProfile.user_id.in_(ids))
        ).scalars()
    }
    tiers = {
        t.customer_id: t
        for t in db.session.execute(
            select(CustomerCreditTier).where(CustomerCreditTier.customer_id.in_(ids))
        ).scalars()
    }

    out: list[dict[str, Any]] = []
    for customer_id, open_count, outstanding_sum, worst in candidates:
        tier_row = tiers.get(customer_id)
        tier_name = tier_row.tier if tier_row else classify(customer_id).tier
        if tier and tier_name != tier:
            continue
        cp = profiles.get(customer_id)
        out.append(
            {
                "customer_id": customer_id,
                "display_name": cp.display_name if cp else None,
                "tier": tier_name,
                "outstanding": str(to_money(outstanding_sum)),
                "open_due_count": open_count,
                "worst_overdue_days": worst,
                "order_block_level": order_block_level(customer_id),
            }
        )
    out.sort(key=lambda r: r["worst_overdue_days"], reverse=True)
    return out


REMINDER_DAYS_BEFORE = 3


def due_reminders() -> int:
    """Proactive reminder (docs/04 §2): notify customers of open dues coming due
    in REMINDER_DAYS_BEFORE days. In-app by default (switch the channel once the
    SMS/WhatsApp provider is configured). Returns the count sent. Intended to run
    once per day from Beat (not idempotent — a second run the same day
    re-reminds, so the task acks early and is not retried)."""
    from ...notifications.services import notify as notify_svc

    target_date = _today() + timedelta(days=REMINDER_DAYS_BEFORE)
    dues = list(
        db.session.execute(
            select(CustomerDue).where(
                CustomerDue.status == "open", CustomerDue.due_date == target_date
            )
        ).scalars()
    )
    for d in dues:
        notify_svc.notify(
            user_id=d.customer_id,
            title="تذكير باستحقاق قادم",
            body=(
                f"لديك ذمة بمبلغ {to_money(d.amount)} ج.م تستحق في "
                f"{d.due_date.isoformat()}. السداد المبكر قد يمنحك خصمًا."
            ),
            type_="due_reminder",
            channel="in_app",
        )
    return len(dues)


def serialize_due(d: CustomerDue) -> dict[str, Any]:
    return {
        "id": d.id,
        "order_id": d.order_id,
        "amount": str(to_money(d.amount)),
        "due_date": d.due_date.isoformat(),
        "status": d.status,
        "paid_date": d.paid_date.isoformat() if d.paid_date else None,
        "days_late": d.days_late,
    }


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
        "order_block_level": order_block_level(customer_id),
    }

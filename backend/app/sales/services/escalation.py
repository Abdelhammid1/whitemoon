"""5-level dunning escalation (US-5.3).

Levels 1–4 run automatically from the overdue-dues scan; level 5 (full
account freeze) is manual-only and requires the `admin.high` role, carrying
the acting admin's id. docs/04-credit-rating-rules.md §2.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from ...common.errors import BadRequest
from ...extensions import db
from ...identity.models import User
from ..models import CustomerDue, EscalationEvent
from . import credit

# Auto level thresholds by max days overdue on any open due.
_AUTO_LEVELS = (
    (1, 1, 7, "تنبيه مبكر — تأخر ١–٧ أيام"),
    (2, 8, 15, "تخفيض سقف الطلبات — تأخر ٨–١٥ يومًا"),
    (3, 16, 30, "تنزيل التصنيف اللوني — تأخر ١٦–٣٠ يومًا"),
    (4, 31, 60, "تجميد الطلبات الجديدة — تأخر ٣١–٦٠ يومًا"),
)

MIN_REASON_LEN = 5


def _max_overdue_days(customer_id: int) -> int:
    today = credit._today()
    open_dues = db.session.execute(
        select(CustomerDue).where(
            CustomerDue.customer_id == customer_id, CustomerDue.status == "open"
        )
    ).scalars().all()
    return max(((today - d.due_date).days for d in open_dues), default=0)


def _already_at_level(customer_id: int, level: int) -> bool:
    row = db.session.execute(
        select(EscalationEvent).where(
            EscalationEvent.customer_id == customer_id, EscalationEvent.level == level
        )
    ).first()
    return row is not None


def _overdue_over_30pct(customer_id: int) -> bool:
    """Total overdue open dues exceed 30% of the customer's limit — the
    secondary Level-3 trigger (docs/04 §2)."""
    today = credit._today()
    open_dues = db.session.execute(
        select(CustomerDue).where(
            CustomerDue.customer_id == customer_id, CustomerDue.status == "open"
        )
    ).scalars().all()
    overdue_sum = sum(
        (d.amount for d in open_dues if (today - d.due_date).days > 0),
        start=Decimal("0"),
    )
    if overdue_sum <= 0:
        return False
    limit = credit.effective_limit(customer_id)
    return limit > 0 and overdue_sum > limit * Decimal("0.30")


def run_for_customer(customer_id: int) -> list[EscalationEvent]:
    """Open the appropriate automatic (1–4) escalation events for one customer
    based on their worst overdue due (and the secondary >30%-of-limit L3
    trigger). Level 3 forces a one-step colour downgrade. Returns new events."""
    overdue = _max_overdue_days(customer_id)
    created: list[EscalationEvent] = []
    for level, lo, hi, reason in _AUTO_LEVELS:
        if lo <= overdue <= hi and not _already_at_level(customer_id, level):
            ev = EscalationEvent(
                customer_id=customer_id, level=level, trigger_reason=reason, is_automatic=True
            )
            db.session.add(ev)
            created.append(ev)
    # Secondary L3 trigger: overdue > 30% of limit, even below 16 days.
    if (
        all(ev.level != 3 for ev in created)
        and not _already_at_level(customer_id, 3)
        and _overdue_over_30pct(customer_id)
    ):
        ev = EscalationEvent(
            customer_id=customer_id,
            level=3,
            trigger_reason="تجاوز المتأخرات ٣٠٪ من السقف",
            is_automatic=True,
        )
        db.session.add(ev)
        created.append(ev)
    # Level 3 → force a one-step colour downgrade; other levels just refresh.
    if any(ev.level == 3 for ev in created):
        credit.apply_l3_downgrade(customer_id)
    elif created:
        credit.recompute(customer_id)
    db.session.commit()
    return created


def run_all() -> int:
    """Scan every customer with an open due and apply levels 1–4."""
    customer_ids = db.session.execute(
        select(CustomerDue.customer_id).where(CustomerDue.status == "open").distinct()
    ).scalars().all()
    total = 0
    for cid in customer_ids:
        total += len(run_for_customer(cid))
    return total


def nightly_scan() -> dict[str, int]:
    """The daily credit maintenance job (docs/04 §1): recompute every active
    customer's tier, then open any due escalation events. Idempotent — safe to
    run repeatedly. Driven by Celery Beat in production; also callable directly.
    """
    recomputed = credit.recompute_all_active()
    opened = run_all()
    de_escalated = credit.de_escalate_all()
    return {
        "recomputed": recomputed,
        "escalations_opened": opened,
        "de_escalated": de_escalated,
    }


def escalate_level5(*, customer_id: int, reason: str, actor_user_id: int) -> EscalationEvent:
    """Manual full freeze (US-5.3). Caller must hold admin.high; the route
    enforces the permission, this records the event and suspends the user."""
    if len(reason.strip()) < MIN_REASON_LEN:
        raise BadRequest("السبب إلزامي (٥ أحرف فأكثر)", code="reason_required")
    ev = EscalationEvent(
        customer_id=customer_id,
        level=5,
        trigger_reason=reason.strip(),
        is_automatic=False,
        actor_user_id=actor_user_id,
    )
    db.session.add(ev)
    user = db.session.get(User, customer_id)
    if user is not None:
        user.status = "suspended"
        user.suspended_at = datetime.now(UTC)
    db.session.commit()
    return ev


def serialize_event(ev: EscalationEvent) -> dict[str, Any]:
    return {
        "id": ev.id,
        "customer_id": ev.customer_id,
        "level": ev.level,
        "trigger_reason": ev.trigger_reason,
        "is_automatic": ev.is_automatic,
        "actor_user_id": ev.actor_user_id,
        "triggered_at": ev.triggered_at.isoformat(),
    }

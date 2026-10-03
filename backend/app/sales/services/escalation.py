"""5-level dunning escalation (US-5.3).

Levels 1–4 run automatically from the overdue-dues scan; level 5 (full
account freeze) is manual-only and requires the `admin.high` role, carrying
the acting admin's id. docs/04-credit-rating-rules.md §2.
"""

from __future__ import annotations

from datetime import UTC, datetime
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
    today = datetime.now(UTC).date()
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


def run_for_customer(customer_id: int) -> list[EscalationEvent]:
    """Open the appropriate automatic (1–4) escalation events for one
    customer based on their worst overdue due. Returns new events."""
    overdue = _max_overdue_days(customer_id)
    created: list[EscalationEvent] = []
    for level, lo, hi, reason in _AUTO_LEVELS:
        if lo <= overdue <= hi and not _already_at_level(customer_id, level):
            ev = EscalationEvent(
                customer_id=customer_id,
                level=level,
                trigger_reason=reason,
                is_automatic=True,
            )
            db.session.add(ev)
            created.append(ev)
            if level == 3:
                # Downgrade one tier toward red immediately.
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

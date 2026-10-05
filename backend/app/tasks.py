"""Celery task definitions — thin wrappers over the service layer.

Keeping the logic in services (not here) means every job is unit-testable by
calling the service function directly, with no worker or broker.
"""

from __future__ import annotations

from .celery_app import celery_app
from .sales.services import credit as credit_svc
from .sales.services import escalation as esc_svc


@celery_app.task(name="credit.nightly_scan")
def nightly_credit_scan() -> dict[str, int]:
    """Daily: recompute every active customer's credit tier and open any due
    escalation events. Scheduled by Celery Beat (see celery_app.beat_schedule)."""
    return esc_svc.nightly_scan()


@celery_app.task(name="credit.due_reminders", acks_late=False)
def due_reminders() -> int:
    """Daily: remind customers of dues coming due in a few days (docs/04 §2).
    acks_late=False (override the global): this task is NOT idempotent, so it
    must not be redelivered on a worker crash and re-send reminders."""
    return credit_svc.due_reminders()


@celery_app.task(name="inventory.reorder_scan")
def reorder_scan() -> dict[str, int]:
    """Daily: open new low-stock alerts and advance the reorder chain (US-4.3)."""
    from .inventory.services import reorder as reorder_svc

    return reorder_svc.scan()


@celery_app.task(name="notifications.dispatch")
def dispatch_notification(notification_id: int) -> bool:
    """Async delivery of a single notification on its external channel."""
    from .notifications.services import notify as notify_svc

    return notify_svc.redispatch(notification_id)

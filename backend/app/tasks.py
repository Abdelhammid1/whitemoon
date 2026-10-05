"""Celery task definitions — thin wrappers over the service layer.

Keeping the logic in services (not here) means every job is unit-testable by
calling the service function directly, with no worker or broker.
"""

from __future__ import annotations

from .celery_app import celery_app
from .sales.services import escalation as esc_svc


@celery_app.task(name="credit.nightly_scan")
def nightly_credit_scan() -> dict[str, int]:
    """Daily: recompute every active customer's credit tier and open any due
    escalation events. Scheduled by Celery Beat (see celery_app.beat_schedule)."""
    return esc_svc.nightly_scan()

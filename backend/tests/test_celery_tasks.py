"""Scheduled credit maintenance (nightly scan) + Celery task registration.

The logic is tested by calling the service functions directly — no broker or
worker is needed.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.extensions import db
from app.sales.services import credit as credit_svc
from app.sales.services import escalation as esc_svc
from tests.helpers import create_user


def test_recompute_all_active_counts_active_customers(client) -> None:
    create_user(kind="customer", email="ra1@example.com", roles=("customer",))
    create_user(kind="customer", email="ra2@example.com", roles=("customer",))
    create_user(kind="customer", email="rasusp@example.com", roles=("customer",), status="suspended")
    db.session.commit()
    assert credit_svc.recompute_all_active() == 2  # suspended excluded


def test_nightly_scan_recomputes_and_escalates(client) -> None:
    cust = create_user(kind="customer", email="nscan@example.com", roles=("customer",))
    db.session.commit()
    credit_svc.record_due(
        customer_id=cust.id, order_id=None, amount=Decimal("500"),
        due_date=date.today() - timedelta(days=20),
    )
    db.session.commit()
    result = esc_svc.nightly_scan()
    assert result["recomputed"] >= 1
    assert result["escalations_opened"] >= 1  # 20 days overdue opens an event


def test_celery_task_registered(client) -> None:
    import app.tasks  # noqa: F401 — importing registers the task
    from app.celery_app import celery_app

    assert "credit.nightly_scan" in celery_app.tasks
    assert "nightly-credit-scan" in celery_app.conf.beat_schedule

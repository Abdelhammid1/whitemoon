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


def test_due_reminders_notifies_upcoming(client) -> None:
    cust = create_user(kind="customer", email="rem@example.com", roles=("customer",))
    db.session.commit()
    # Due in exactly 3 days → reminded; due in 10 days → not.
    credit_svc.record_due(customer_id=cust.id, order_id=None, amount=Decimal("400"), due_date=date.today() + timedelta(days=3))
    credit_svc.record_due(customer_id=cust.id, order_id=None, amount=Decimal("400"), due_date=date.today() + timedelta(days=10))
    db.session.commit()
    assert credit_svc.due_reminders() == 1
    from app.notifications.services import notify as notify_svc
    assert any(n.type == "due_reminder" for n in notify_svc.list_for(cust.id))


def test_external_channel_delivery_noop_when_unconfigured(client) -> None:
    from app.notifications.providers.delivery import deliver
    from app.notifications.services import notify as notify_svc

    # No provider env in tests → graceful no-op (never raises).
    assert deliver(channel="sms", target="+201000000000", title="t", body="b") is False
    assert deliver(channel="email", target="x@example.com", title="t", body="b") is False
    assert deliver(channel="sms", target=None, title="t", body=None) is False
    # notify() on an external channel still succeeds and stores the row.
    cust = create_user(kind="customer", email="smsuser@example.com", phone="+201111111111", roles=("customer",))
    db.session.commit()
    n = notify_svc.notify(user_id=cust.id, title="تنبيه", channel="sms")
    assert n.id is not None and n.channel == "sms"


def test_celery_tasks_registered(client) -> None:
    import app.tasks  # noqa: F401 — importing registers the tasks
    from app.celery_app import celery_app

    assert "credit.nightly_scan" in celery_app.tasks
    assert "credit.due_reminders" in celery_app.tasks
    assert "notifications.dispatch" in celery_app.tasks
    assert "nightly-credit-scan" in celery_app.conf.beat_schedule
    assert "daily-due-reminders" in celery_app.conf.beat_schedule

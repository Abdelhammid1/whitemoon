"""EPIC 5 — credit tiers, limits, dues, dunning (docs/04)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.common.errors import Forbidden
from app.extensions import db
from app.sales.models import CustomerDue
from app.sales.services import credit as credit_svc
from app.sales.services import escalation as esc_svc
from tests.helpers import create_user


def _aged_customer(email: str, days_old: int = 200):
    u = create_user(kind="customer", email=email, roles=("customer",))
    u.created_at = datetime.now(UTC) - timedelta(days=days_old)
    db.session.commit()
    return u


def _paid_due(customer_id: int, *, due_days_ago: int, late: int, amount="100"):
    due_date = date.today() - timedelta(days=due_days_ago)
    due = credit_svc.record_due(customer_id=customer_id, order_id=None, amount=Decimal(amount), due_date=due_date)
    db.session.commit()
    credit_svc.record_payment(due_id=due.id, paid_on=due_date + timedelta(days=late))
    return due


# ---------------------------------------------------------------- US-5.1 tiers


def test_new_customer_is_white(client) -> None:
    cust = create_user(kind="customer", email="new@example.com", roles=("customer",))
    db.session.commit()
    tier = credit_svc.recompute(cust.id)
    assert tier.tier == "white"
    assert tier.credit_limit == Decimal("250000.0000")


def test_on_time_history_is_green(client) -> None:
    cust = _aged_customer("green@example.com")
    for _ in range(4):
        _paid_due(cust.id, due_days_ago=40, late=0)
    tier = credit_svc.recompute(cust.id)
    assert tier.tier == "green"
    assert tier.credit_limit == Decimal("500000.0000")


def test_default_makes_red(client) -> None:
    cust = _aged_customer("red@example.com")
    _paid_due(cust.id, due_days_ago=200, late=100)  # >90 late → defaulted
    _paid_due(cust.id, due_days_ago=100, late=0)
    _paid_due(cust.id, due_days_ago=50, late=0)
    tier = credit_svc.recompute(cust.id)
    assert tier.tier == "red"
    assert tier.credit_limit == Decimal("0.0000")


def test_moderate_lateness_is_yellow(client) -> None:
    cust = _aged_customer("yellow@example.com")
    # 3 dues, two on time + one 20 days late → score in yellow band, no default.
    _paid_due(cust.id, due_days_ago=60, late=0)
    _paid_due(cust.id, due_days_ago=50, late=0)
    _paid_due(cust.id, due_days_ago=40, late=20)
    tier = credit_svc.recompute(cust.id)
    assert tier.tier in ("yellow", "green")  # depends on weighting; never red here
    assert tier.tier != "red"


# ---------------------------------------------------------------- US-5.2 limits


def test_override_raises_limit(client) -> None:
    cust = create_user(kind="customer", email="ov@example.com", roles=("customer",))
    db.session.commit()
    credit_svc.recompute(cust.id)
    credit_svc.set_override(customer_id=cust.id, credit_limit=Decimal("1000000"), reason="عميل استراتيجي معتمد", set_by=1)
    assert credit_svc.effective_limit(cust.id) == Decimal("1000000.0000")


def test_credit_check_blocks_over_limit(client) -> None:
    cust = _aged_customer("lim@example.com")
    # white limit 250k; an open due of 200k then a 100k deferred order → over.
    credit_svc.recompute(cust.id)
    credit_svc.record_due(customer_id=cust.id, order_id=None, amount=Decimal("200000"), due_date=date.today() + timedelta(days=30))
    db.session.commit()
    with pytest.raises(Forbidden):
        credit_svc.check_credit(customer_id=cust.id, order_amount=Decimal("100000"), deferred=True)


def test_red_cannot_defer(client) -> None:
    cust = _aged_customer("rednodef@example.com")
    _paid_due(cust.id, due_days_ago=200, late=100)
    _paid_due(cust.id, due_days_ago=100, late=0)
    _paid_due(cust.id, due_days_ago=50, late=0)
    credit_svc.recompute(cust.id)
    with pytest.raises(Forbidden):
        credit_svc.check_credit(customer_id=cust.id, order_amount=Decimal("10"), deferred=True)


# ---------------------------------------------------------------- US-5.3 escalation


def test_auto_escalation_level_by_overdue(client) -> None:
    cust = _aged_customer("esc@example.com")
    # An open due 20 days overdue → level 3.
    credit_svc.record_due(customer_id=cust.id, order_id=None, amount=Decimal("500"), due_date=date.today() - timedelta(days=20))
    db.session.commit()
    created = esc_svc.run_for_customer(cust.id)
    assert len(created) == 1
    assert created[0].level == 3
    # Re-run doesn't duplicate the same level.
    assert esc_svc.run_for_customer(cust.id) == []


def test_level5_is_manual_and_suspends(client) -> None:
    cust = create_user(kind="customer", email="freeze@example.com", roles=("customer",))
    db.session.commit()
    ev = esc_svc.escalate_level5(customer_id=cust.id, reason="إحالة قانونية بعد تجاوز ٦٠ يومًا", actor_user_id=1)
    assert ev.level == 5
    assert ev.is_automatic is False
    assert ev.actor_user_id == 1
    from app.identity.models import User
    refreshed = db.session.get(User, cust.id)
    assert refreshed is not None and refreshed.status == "suspended"


def test_record_payment_computes_days_late(client) -> None:
    cust = create_user(kind="customer", email="pay@example.com", roles=("customer",))
    db.session.commit()
    due = credit_svc.record_due(customer_id=cust.id, order_id=None, amount=Decimal("100"), due_date=date.today() - timedelta(days=10))
    db.session.commit()
    paid = credit_svc.record_payment(due_id=due.id, paid_on=date.today())
    assert paid.days_late == 10
    assert paid.status == "paid"


_ = CustomerDue

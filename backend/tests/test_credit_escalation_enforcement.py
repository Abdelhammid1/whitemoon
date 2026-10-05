"""US-5.3 — automatic escalation ENFORCEMENT at checkout (docs/04 §2).

Beyond recording escalation events, the credit check must act on the
customer's current overdue standing: L2 (8–30 days, or two dues ≥7 days, or
overdue >30% of limit) halves the limit and blocks new deferred; L4 (≥31 days)
rejects all new orders until settled. These are derived from live open dues, so
they clear on settlement. A manual override lifts L2 but not L4.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.common.errors import Forbidden
from app.extensions import db
from app.sales.services import credit as cs
from tests.helpers import create_user


def _cust(email: str):
    u = create_user(kind="customer", email=email, roles=("customer",))
    db.session.commit()
    return u


def _open_due(cid: int, *, days_overdue: int, amount: str = "1000"):
    cs.record_due(
        customer_id=cid,
        order_id=None,
        amount=Decimal(amount),
        due_date=date.today() - timedelta(days=days_overdue),
    )
    db.session.commit()


def test_no_overdue_no_block(client) -> None:
    c = _cust("e_none@example.com")
    assert cs.order_block_level(c.id) == 0
    cs.check_credit(customer_id=c.id, order_amount=Decimal("1000"), deferred=True)  # no raise


def test_l2_blocks_deferred_and_halves_limit(client) -> None:
    c = _cust("e_l2@example.com")
    _open_due(c.id, days_overdue=10)  # 8–30 → L2
    assert cs.order_block_level(c.id) == 2
    assert cs.effective_limit(c.id) == Decimal("125000.0000")  # white 250k halved
    with pytest.raises(Forbidden) as e:
        cs.check_credit(customer_id=c.id, order_amount=Decimal("10"), deferred=True)
    assert e.value.code == "deferred_blocked_escalation"
    # Cash is still allowed at L2.
    cs.check_credit(customer_id=c.id, order_amount=Decimal("10"), deferred=False)


def test_l2_two_dues_over_7_days(client) -> None:
    c = _cust("e_two@example.com")
    _open_due(c.id, days_overdue=7)
    _open_due(c.id, days_overdue=7)
    assert cs.order_block_level(c.id) == 2  # two dues ≥7 days, even if <8


def test_low_days_large_overdue_is_not_an_l2_block(client) -> None:
    # A due only 5 days late (L1 reminder window) does not block deferred,
    # regardless of amount — large overdue exposure is an L3 downgrade trigger
    # per docs/04 §2, not an L2 order block.
    c = _cust("e_30@example.com")
    _open_due(c.id, days_overdue=5, amount="80000")
    assert cs.order_block_level(c.id) == 0


def test_l4_blocks_all_orders(client) -> None:
    c = _cust("e_l4@example.com")
    _open_due(c.id, days_overdue=40)  # 31–60 → L4
    assert cs.order_block_level(c.id) == 4
    for deferred in (False, True):
        with pytest.raises(Forbidden) as e:
            cs.check_credit(customer_id=c.id, order_amount=Decimal("10"), deferred=deferred)
        assert e.value.code == "orders_frozen_overdue"


def test_override_lifts_l2_not_the_cut_target(client) -> None:
    c = _cust("e_ov@example.com")
    _open_due(c.id, days_overdue=10)  # L2
    cs.set_override(customer_id=c.id, credit_limit=Decimal("300000"), reason="استثناء معتمد من الإدارة", set_by=1)
    # Override wins the limit — no 50% auto-cut on top of it.
    assert cs.effective_limit(c.id) == Decimal("300000.0000")
    # The block level itself reads 0 for an override customer, so the UI banner
    # does not claim an enforcement that is not in effect.
    assert cs.order_block_level(c.id) == 0
    assert cs.serialize_tier(c.id)["order_block_level"] == 0
    # Deferred is allowed again (the override lifts the L2 block).
    cs.check_credit(customer_id=c.id, order_amount=Decimal("10"), deferred=True)


def test_override_does_not_lift_l4(client) -> None:
    c = _cust("e_ov4@example.com")
    _open_due(c.id, days_overdue=40)  # L4
    cs.set_override(customer_id=c.id, credit_limit=Decimal("300000"), reason="استثناء معتمد من الإدارة", set_by=1)
    with pytest.raises(Forbidden) as e:
        cs.check_credit(customer_id=c.id, order_amount=Decimal("10"), deferred=True)
    assert e.value.code == "orders_frozen_overdue"


def test_block_clears_after_settlement(client) -> None:
    c = _cust("e_clear@example.com")
    due = cs.record_due(
        customer_id=c.id, order_id=None, amount=Decimal("1000"),
        due_date=date.today() - timedelta(days=10),
    )
    db.session.commit()
    assert cs.order_block_level(c.id) == 2
    cs.record_payment(due_id=due.id, paid_on=date.today())  # settle
    assert cs.order_block_level(c.id) == 0


def test_serialize_tier_exposes_block_level(client) -> None:
    c = _cust("e_ser@example.com")
    _open_due(c.id, days_overdue=40)
    assert cs.serialize_tier(c.id)["order_block_level"] == 4

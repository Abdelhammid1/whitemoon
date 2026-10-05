"""Reorder low-stock escalation chain, levels 1→4 (US-4.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.extensions import db
from app.inventory.models import ReorderAlert, StockBalance
from app.inventory.services import products as psvc
from app.inventory.services import reorder as svc
from tests.helpers import create_user


def _low_balance(email: str):
    sup = create_user(kind="supplier", email=email, roles=("supplier",))
    p = psvc.create_product(sku=f"RE-{email[:4]}", name_ar="صنف", category="food", created_by=1)
    db.session.commit()
    bal = StockBalance(
        supplier_id=sup.id, product_id=p.id, location_type="supplier",
        on_hand=Decimal("0"), reorder_point=Decimal("10"),
    )
    db.session.add(bal)
    db.session.commit()
    return sup, bal


def _open_alert(bal_id: int) -> ReorderAlert:
    return db.session.execute(
        db.select(ReorderAlert).where(
            ReorderAlert.stock_balance_id == bal_id, ReorderAlert.acknowledged_at.is_(None)
        )
    ).scalar_one()


def test_check_opens_level1(client) -> None:
    _sup, bal = _low_balance("rl1@example.com")
    created = svc.check()
    assert any(a.stock_balance_id == bal.id and a.level == 1 for a in created)


def test_escalate_climbs_to_supplier(client) -> None:
    sup, bal = _low_balance("rl2@example.com")
    svc.check()
    for expected in (2, 3, 4):
        a = _open_alert(bal.id)
        a.triggered_at = datetime.now(UTC) - timedelta(hours=25)
        db.session.commit()
        assert svc.escalate()["advanced"] == 1
        assert a.level == expected
    # Reaching level 4 fires a restock notification to the supplier.
    from app.notifications.services import notify as notify_svc
    assert any(n.type == "reorder" for n in notify_svc.list_for(sup.id))


def test_escalate_closes_on_restock(client) -> None:
    _sup, bal = _low_balance("rl3@example.com")
    svc.check()
    a = _open_alert(bal.id)
    a.triggered_at = datetime.now(UTC) - timedelta(hours=25)
    bal.on_hand = Decimal("50")  # restocked above the reorder point
    db.session.commit()
    assert svc.escalate()["closed"] == 1
    assert a.acknowledged_at is not None


def test_acknowledge(client) -> None:
    _sup, bal = _low_balance("rl4@example.com")
    svc.check()
    a = _open_alert(bal.id)
    svc.acknowledge(alert_id=a.id, user_id=1)
    assert a.acknowledged_at is not None

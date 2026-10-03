"""EPIC 9 — logistics: slot capacity, tracking, delivery confirmation."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.commerce.models import Order
from app.common.errors import Conflict, Forbidden
from app.extensions import db
from app.inventory.services import products as products_svc
from app.logistics.services import logistics as svc
from app.logistics.services.logistics import ShortageInput
from tests.helpers import create_user


def _customer():
    u = create_user(kind="customer", email=f"c{uuid.uuid4().hex[:6]}@example.com", roles=("customer",))
    db.session.commit()
    return u


def _order(customer_id: int):
    o = Order(
        number=f"ORD-{uuid.uuid4().hex[:10]}",
        customer_id=customer_id,
        status="confirmed",
        payment_mode="cash",
        total_cash=Decimal("100"),
        total_deferred=Decimal("100"),
    )
    db.session.add(o)
    db.session.commit()
    return o


def _slot(capacity: int = 1, days: int = 1):
    return svc.create_slot(slot_date=date.today() + timedelta(days=days), window="09:00-11:00", capacity=capacity)


def test_slot_capacity_blocks_overbooking(client) -> None:
    slot = _slot(capacity=1)
    c1, c2 = _customer(), _customer()
    o1, o2 = _order(c1.id), _order(c2.id)
    svc.book_slot(order_id=o1.id, slot_id=slot.id, actor_user_id=c1.id)
    with pytest.raises(Conflict):
        svc.book_slot(order_id=o2.id, slot_id=slot.id, actor_user_id=c2.id)
    # Full slot drops out of the available list.
    avail = svc.available_slots(date_from=date.today(), date_to=date.today() + timedelta(days=3))
    assert slot.id not in [s.id for s in avail]


def test_booking_returns_confirmation_code(client) -> None:
    slot = _slot(capacity=5)
    c = _customer()
    o = _order(c.id)
    shipment = svc.book_slot(order_id=o.id, slot_id=slot.id, actor_user_id=c.id)
    assert shipment.status == "scheduled"
    assert len(shipment.confirmation_code) == 8  # 8 hex chars, not a 6-digit PIN


def test_cannot_book_cancelled_order(client) -> None:
    slot = _slot(capacity=5)
    c = _customer()
    o = _order(c.id)
    o.status = "cancelled"
    db.session.commit()
    with pytest.raises(Conflict):
        svc.book_slot(order_id=o.id, slot_id=slot.id, actor_user_id=c.id)


def test_tracking_status_flow_and_location(client) -> None:
    slot = _slot(capacity=5)
    c = _customer()
    o = _order(c.id)
    s = svc.book_slot(order_id=o.id, slot_id=slot.id, actor_user_id=c.id)
    svc.update_status(shipment_id=s.id, status="shipped", actor_user_id=1)
    s2 = svc.update_location(shipment_id=s.id, lat=Decimal("30.044"), lng=Decimal("31.235"))
    assert s2.status == "in_transit"
    assert s2.current_lat == Decimal("30.044000")


def test_confirm_delivery_requires_proof_and_logs_shortage(client) -> None:
    slot = _slot(capacity=5)
    c = _customer()
    o = _order(c.id)
    product = products_svc.create_product(sku=f"P-{uuid.uuid4().hex[:6]}", name_ar="صنف", category="food", created_by=1)
    s = svc.book_slot(order_id=o.id, slot_id=slot.id, actor_user_id=c.id)

    # Wrong code is rejected.
    with pytest.raises(Forbidden):
        svc.confirm_delivery(shipment_id=s.id, delivered_by=1, confirmation_code="000000")

    done = svc.confirm_delivery(
        shipment_id=s.id,
        delivered_by=1,
        confirmation_code=s.confirmation_code,
        shortages=[ShortageInput(product_id=product.id, qty=Decimal("2"), photo_url="https://x/y.jpg", note="تالف")],
    )
    assert done.status == "delivered"
    assert done.delivered_at is not None
    assert len(done.shortages) == 1
    assert done.shortages[0].photo_url == "https://x/y.jpg"


def test_confirm_delivery_by_signature(client) -> None:
    slot = _slot(capacity=5)
    c = _customer()
    o = _order(c.id)
    s = svc.book_slot(order_id=o.id, slot_id=slot.id, actor_user_id=c.id)
    done = svc.confirm_delivery(shipment_id=s.id, delivered_by=1, signature="data:image/png;base64,AAA")
    assert done.status == "delivered"
    assert done.signature is not None

"""Operational-gap tickets: T-01 geo scope, T-02 payment approval,
T-03 cross-sell, T-05 shipment legs, T-10 product variants."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.common.errors import Forbidden
from app.extensions import db
from app.identity.models import ChannelPartnerProfile, CustomerProfile
from tests.helpers import create_user


def _customer(email: str, geo: str | None = None):
    u = create_user(kind="customer", email=email, roles=("customer",))
    db.session.add(CustomerProfile(user_id=u.id, display_name="عميل", geo_area=geo))
    db.session.commit()
    return u


def _partner(email: str, geo: str, ptype: str = "agent"):
    u = create_user(kind=ptype, email=email, roles=(ptype,))
    db.session.add(ChannelPartnerProfile(user_id=u.id, type=ptype, display_name="شريك", geo_scope=geo))
    db.session.commit()
    return u


# ---------------------------------------------------------------- T-02


def test_payment_approval_one_level(client) -> None:
    from app.sales.services import credit as credit_svc
    from app.sales.services import payments as pay_svc

    cust = create_user(kind="customer", email=f"p{uuid.uuid4().hex[:6]}@example.com", roles=("customer",))
    collector = create_user(kind="staff", email=f"col{uuid.uuid4().hex[:6]}@example.com", roles=("staff",))
    approver = create_user(kind="admin", email=f"apr{uuid.uuid4().hex[:6]}@example.com", roles=("admin",))
    db.session.commit()
    due = credit_svc.record_due(
        customer_id=cust.id, order_id=None, amount=Decimal("500"), due_date=date.today()
    )
    db.session.commit()

    appr = pay_svc.collect_payment(
        customer_id=cust.id, due_id=due.id, amount=Decimal("500"), paid_on=date.today(), collected_by=collector.id
    )
    assert appr.status == "pending"

    # The collector cannot approve their own collection (one level).
    with pytest.raises(Forbidden):
        pay_svc.approve_payment(approval_id=appr.id, approver_id=collector.id)

    # A different approver applies it; the due becomes paid.
    done = pay_svc.approve_payment(approval_id=appr.id, approver_id=approver.id)
    assert done.status == "approved"
    refreshed = db.session.get(type(due), due.id)
    assert refreshed.status == "paid"


# ---------------------------------------------------------------- T-01


def test_customer_in_scope(client) -> None:
    from app.partners.services import partners as partners_svc

    agent = _partner(f"a{uuid.uuid4().hex[:6]}@example.com", geo="القاهرة")
    inside = _customer(f"in{uuid.uuid4().hex[:6]}@example.com", geo="القاهرة")
    outside = _customer(f"out{uuid.uuid4().hex[:6]}@example.com", geo="الإسكندرية")
    assert partners_svc.customer_in_scope(agent.id, inside.id) is True
    assert partners_svc.customer_in_scope(agent.id, outside.id) is False


# ---------------------------------------------------------------- T-03


def test_cross_sell_same_category(client) -> None:
    from app.commerce.services import catalog as catalog_svc
    from app.inventory.services import offers as offers_svc
    from app.inventory.services import products as products_svc

    sup = create_user(kind="supplier", email=f"s{uuid.uuid4().hex[:6]}@example.com", roles=("supplier",))
    db.session.commit()
    p1 = products_svc.create_product(sku=f"A-{uuid.uuid4().hex[:6]}", name_ar="صنف1", category="food", created_by=1)
    p2 = products_svc.create_product(sku=f"B-{uuid.uuid4().hex[:6]}", name_ar="صنف2", category="food", created_by=1)
    p3 = products_svc.create_product(sku=f"C-{uuid.uuid4().hex[:6]}", name_ar="صنف3", category="clothing", created_by=1)
    for p in (p1, p2, p3):
        offers_svc.upsert_offer(supplier_id=sup.id, product_id=p.id, unit_price=Decimal("10"))
    db.session.commit()
    related = catalog_svc.related_products(p1.id)
    ids = {r["product_id"] for r in related}
    assert p2.id in ids and p3.id not in ids and p1.id not in ids


# ---------------------------------------------------------------- T-10


def test_product_variant_and_fields(client) -> None:
    from app.inventory.services import products as products_svc

    p = products_svc.create_product(
        sku=f"V-{uuid.uuid4().hex[:6]}", name_ar="قميص", category="clothing", created_by=1,
        brand="براند", barcode="6221000000001", description="وصف", subcategory="قمصان",
    )
    products_svc.add_variant(product_id=p.id, sku=f"V-{uuid.uuid4().hex[:6]}-L", barcode=None, size="L", color="أزرق")
    data = products_svc.serialize(products_svc.get_product(p.id))
    assert data["brand"] == "براند"
    assert data["subcategory"] == "قمصان"
    assert len(data["variants"]) == 1
    assert data["variants"][0]["size"] == "L"


# ---------------------------------------------------------------- T-05


def test_shipment_legs(client) -> None:
    from app.commerce.models import Order
    from app.logistics.services import logistics as svc

    cust = create_user(kind="customer", email=f"l{uuid.uuid4().hex[:6]}@example.com", roles=("customer",))
    order = Order(
        number=f"ORD-{uuid.uuid4().hex[:8]}", customer_id=cust.id, status="confirmed",
        payment_mode="cash", total_cash=Decimal("100"), total_deferred=Decimal("100"),
    )
    db.session.add(order)
    db.session.commit()
    slot = svc.create_slot(slot_date=date.today() + timedelta(days=1), window="09:00-11:00", capacity=5)
    ship = svc.book_slot(order_id=order.id, slot_id=slot.id, actor_user_id=cust.id)

    svc.add_leg(shipment_id=ship.id, carrier_type="internal", carrier_ref=None, from_label="المخزن", to_label="مركز الفرز")
    svc.add_leg(shipment_id=ship.id, carrier_type="external", carrier_ref="SHIP-CO", from_label="مركز الفرز", to_label="العميل")
    data = svc.serialize_shipment(ship)
    assert [lg["carrier_type"] for lg in data["legs"]] == ["internal", "external"]
    # The shipment's own status stays a single unified value.
    assert data["status"] == "scheduled"

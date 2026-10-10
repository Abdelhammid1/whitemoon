"""T-41 — supplier action dashboard: the three cards + confirm/ready quick actions."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.commerce.services import cart as cart_svc
from app.commerce.services import orders as orders_svc
from app.commerce.services import supplier_home as sh_svc
from app.common.errors import Conflict, Forbidden
from app.extensions import db
from app.identity.models import CustomerProfile
from app.inventory.services import offers as offers_svc
from app.inventory.services import products as products_svc
from app.inventory.services import stock as stock_svc
from tests.helpers import auth_header, create_user


def _uniq(p: str) -> str:
    return f"{p}{uuid.uuid4().hex[:6]}@wm.eg"


def _supplier():
    return create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))


def _customer():
    c = create_user(kind="customer", email=_uniq("cust"), roles=("customer",))
    db.session.add(CustomerProfile(user_id=c.id, display_name="عميل"))
    db.session.commit()
    return c


def test_summary_three_cards(client) -> None:
    sup = _supplier()
    prod = products_svc.create_product(sku=f"P-{uuid.uuid4().hex[:6]}", name_ar="صنف", category="food", created_by=1)
    offer = offers_svc.upsert_offer(supplier_id=sup.id, product_id=prod.id, unit_price=Decimal("100"))
    # Low stock: on_hand <= reorder_point.
    stock_svc.manual_adjust(supplier_id=sup.id, product_id=prod.id, location_type="supplier", location_id=None, delta=Decimal("5"), reorder_point=Decimal("10"))
    # Expiring discount (ends in 3 days) — must still be platform-best (no competitors here).
    offers_svc.upsert_offer(
        supplier_id=sup.id, product_id=prod.id, unit_price=Decimal("100"),
        discount_kind="percent", discount_value=Decimal("10"),
        discount_end=date.today() + timedelta(days=3),
    )
    # A customer order → a pending sub-order for the supplier.
    cust = _customer()
    cart_svc.add_item(customer_id=cust.id, offer_id=offer.id, qty=Decimal("1"))
    orders_svc.checkout(customer_id=cust.id, payment_mode="cash")

    s = sh_svc.action_summary(sup.id)
    assert s["counts"]["new_orders"] == 1
    assert s["counts"]["low_stock"] == 1
    assert s["counts"]["expiring_discounts"] == 1


def test_supplier_confirm_then_ready(client) -> None:
    sup = _supplier()
    prod = products_svc.create_product(sku=f"P-{uuid.uuid4().hex[:6]}", name_ar="صنف", category="food", created_by=1)
    offer = offers_svc.upsert_offer(supplier_id=sup.id, product_id=prod.id, unit_price=Decimal("100"))
    cust = _customer()
    cart_svc.add_item(customer_id=cust.id, offer_id=offer.id, qty=Decimal("1"))
    order = orders_svc.checkout(customer_id=cust.id, payment_mode="cash")
    sub_id = sh_svc.action_summary(sup.id)["new_orders"][0]["sub_order_id"]

    h = auth_header(client, email=sup.email)
    r = client.post(f"/commerce/supplier/sub-orders/{sub_id}/confirm", headers=h)
    assert r.status_code == 200 and r.get_json()["status"] == "confirmed"
    r = client.post(f"/commerce/supplier/sub-orders/{sub_id}/ready", headers=h)
    assert r.status_code == 200 and r.get_json()["status"] == "ready"
    assert order.id  # order exists; sub advanced independently


def test_cannot_advance_other_suppliers_suborder(client) -> None:
    sup = _supplier()
    other = _supplier()
    prod = products_svc.create_product(sku=f"P-{uuid.uuid4().hex[:6]}", name_ar="صنف", category="food", created_by=1)
    offer = offers_svc.upsert_offer(supplier_id=sup.id, product_id=prod.id, unit_price=Decimal("100"))
    cust = _customer()
    cart_svc.add_item(customer_id=cust.id, offer_id=offer.id, qty=Decimal("1"))
    orders_svc.checkout(customer_id=cust.id, payment_mode="cash")
    sub_id = sh_svc.action_summary(sup.id)["new_orders"][0]["sub_order_id"]

    with pytest.raises(Forbidden):
        sh_svc.advance_suborder(supplier_id=other.id, sub_order_id=sub_id, action="confirm")
    # Bad transition: ready before confirm.
    with pytest.raises(Conflict):
        sh_svc.advance_suborder(supplier_id=sup.id, sub_order_id=sub_id, action="ready")


def test_summary_requires_supplier(client) -> None:
    cust = _customer()
    h = auth_header(client, email=cust.email)
    assert client.get("/commerce/supplier/summary", headers=h).status_code == 403

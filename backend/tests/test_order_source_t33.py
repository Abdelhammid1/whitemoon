"""T-33 — order source + per-supplier detail: source attributed to the
customer's territory agent (commission basis), per-supplier sub-orders with
status, and an independent notification to each supplier (no customer data)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select

from app.commerce.services import cart as cart_svc
from app.commerce.services import orders as orders_svc
from app.extensions import db
from app.identity.models import ChannelPartnerProfile, CustomerProfile
from app.inventory.services import offers as offers_svc
from app.inventory.services import products as products_svc
from app.notifications.models import Notification
from tests.helpers import create_user


def _uniq(p: str) -> str:
    return f"{p}{uuid.uuid4().hex[:6]}@wm.eg"


def _supplier_with_product(price: str):
    sup = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    prod = products_svc.create_product(
        sku=f"P-{uuid.uuid4().hex[:6]}", name_ar="صنف", category="food", created_by=1
    )
    offer = offers_svc.upsert_offer(supplier_id=sup.id, product_id=prod.id, unit_price=Decimal(price))
    return sup, prod, offer


def test_two_supplier_order_splits_and_notifies(client) -> None:
    sa, _pa, oa = _supplier_with_product("100")
    sb, _pb, ob = _supplier_with_product("50")
    cust = create_user(kind="customer", email=_uniq("cust"), roles=("customer",))
    db.session.add(CustomerProfile(user_id=cust.id, display_name="عميل", geo_area="القاهرة"))
    # An agent whose territory covers the customer → the order's source.
    agent = create_user(kind="agent", email=_uniq("agt"), roles=("agent",))
    db.session.add(ChannelPartnerProfile(user_id=agent.id, type="agent", display_name="وكيل القاهرة", geo_scope="القاهرة"))
    db.session.commit()

    cart_svc.add_item(customer_id=cust.id, offer_id=oa.id, qty=Decimal("2"))
    cart_svc.add_item(customer_id=cust.id, offer_id=ob.id, qty=Decimal("3"))
    order = orders_svc.checkout(customer_id=cust.id, payment_mode="cash")

    # Source attributed to the agent (commission basis) — by name.
    assert order.partner_user_id == agent.id
    admin = orders_svc.serialize_admin(order)
    assert admin["source"]["type"] == "agent" and admin["source"]["name"] == "وكيل القاهرة"
    # Two sub-orders, each with its own status + subtotal.
    assert len(admin["sub_orders"]) == 2
    assert all("status" in s and "subtotal" in s for s in admin["sub_orders"])

    # Customer view: source + per-part status, NO supplier identity.
    cust_view = orders_svc.serialize_order(order, for_customer=True)
    assert cust_view["source"]["name"] == "وكيل القاهرة"
    assert len(cust_view["parts"]) == 2
    assert "sub_orders" not in cust_view
    assert "supplier_id" not in str(cust_view["parts"])

    # Each supplier was notified of THEIR part only.
    for sup in (sa, sb):
        n = db.session.execute(
            select(Notification).where(Notification.user_id == sup.id, Notification.type == "suborder_new")
        ).scalars().all()
        assert len(n) == 1
        assert str(cust.id) not in (n[0].body or "")  # no customer data


def test_company_direct_when_no_territory_agent(client) -> None:
    _sa, _pa, oa = _supplier_with_product("100")
    cust = create_user(kind="customer", email=_uniq("cust"), roles=("customer",))
    db.session.add(CustomerProfile(user_id=cust.id, display_name="عميل", geo_area="أسوان"))
    db.session.commit()
    cart_svc.add_item(customer_id=cust.id, offer_id=oa.id, qty=Decimal("1"))
    order = orders_svc.checkout(customer_id=cust.id, payment_mode="cash")
    assert order.partner_user_id is None
    assert orders_svc.serialize_admin(order)["source"]["type"] == "company"


def test_ambiguous_territory_is_company(client) -> None:
    # Two agents cover the same area → ambiguous → company-direct.
    _sa, _pa, oa = _supplier_with_product("100")
    cust = create_user(kind="customer", email=_uniq("cust"), roles=("customer",))
    db.session.add(CustomerProfile(user_id=cust.id, display_name="عميل", geo_area="طنطا"))
    for _ in range(2):
        a = create_user(kind="agent", email=_uniq("agt"), roles=("agent",))
        db.session.add(ChannelPartnerProfile(user_id=a.id, type="agent", display_name="وكيل", geo_scope="طنطا"))
    db.session.commit()
    cart_svc.add_item(customer_id=cust.id, offer_id=oa.id, qty=Decimal("1"))
    order = orders_svc.checkout(customer_id=cust.id, payment_mode="cash")
    assert order.partner_user_id is None

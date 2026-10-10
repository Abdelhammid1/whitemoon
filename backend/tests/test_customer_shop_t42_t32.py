"""T-42 reorder + usual items; T-32 usual categories."""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.commerce.services import cart as cart_svc
from app.commerce.services import customer_shop as shop_svc
from app.commerce.services import orders as orders_svc
from app.extensions import db
from app.identity.models import CustomerProfile
from app.inventory.services import offers as offers_svc
from app.inventory.services import products as products_svc
from tests.helpers import auth_header, create_user


def _uniq(p: str) -> str:
    return f"{p}{uuid.uuid4().hex[:6]}@wm.eg"


def _product(price: str, category: str = "food"):
    sup = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    prod = products_svc.create_product(sku=f"P-{uuid.uuid4().hex[:6]}", name_ar="صنف", category=category, created_by=1)
    offer = offers_svc.upsert_offer(supplier_id=sup.id, product_id=prod.id, unit_price=Decimal(price))
    return prod, offer


def _customer():
    c = create_user(kind="customer", email=_uniq("cust"), roles=("customer",))
    db.session.add(CustomerProfile(user_id=c.id, display_name="عميل"))
    db.session.commit()
    return c


def test_reorder_adds_items_and_flags_price_change(client) -> None:
    prod, offer = _product("100")
    cust = _customer()
    cart_svc.add_item(customer_id=cust.id, offer_id=offer.id, qty=Decimal("2"))
    order = orders_svc.checkout(customer_id=cust.id, payment_mode="cash")

    # Price rises after the order; reorder flags it.
    offers_svc.upsert_offer(supplier_id=offer.supplier_id, product_id=prod.id, unit_price=Decimal("120"))
    res = shop_svc.reorder(customer_id=cust.id, order_id=order.id)
    assert res["added"] == 1
    assert any(w["reason"] == "price_changed" and w["new_price"] == "120.0000" for w in res["warnings"])
    # The item is now in a fresh active cart.
    assert len(cart_svc.get_or_create_active_cart(cust.id).items) == 1


def test_reorder_flags_unavailable(client) -> None:
    prod, offer = _product("100")
    cust = _customer()
    cart_svc.add_item(customer_id=cust.id, offer_id=offer.id, qty=Decimal("1"))
    order = orders_svc.checkout(customer_id=cust.id, payment_mode="cash")
    # Deactivate the only offer → unavailable on reorder.
    offers_svc.upsert_offer(supplier_id=offer.supplier_id, product_id=prod.id, unit_price=Decimal("100"), is_active=False)
    res = shop_svc.reorder(customer_id=cust.id, order_id=order.id)
    assert res["added"] == 0
    assert res["warnings"][0]["reason"] == "unavailable"


def test_usual_items_ranked(client) -> None:
    pa, oa = _product("10")
    pb, ob = _product("20")
    cust = _customer()
    # Buy A twice, B once.
    for _ in range(2):
        cart_svc.add_item(customer_id=cust.id, offer_id=oa.id, qty=Decimal("1"))
        orders_svc.checkout(customer_id=cust.id, payment_mode="cash")
    cart_svc.add_item(customer_id=cust.id, offer_id=ob.id, qty=Decimal("1"))
    orders_svc.checkout(customer_id=cust.id, payment_mode="cash")

    items = shop_svc.usual_items(customer_id=cust.id)
    assert items[0]["product_id"] == pa.id  # most frequent first
    assert {i["product_id"] for i in items} == {pa.id, pb.id}


def test_usual_categories_and_endpoint(client) -> None:
    _pf, of = _product("10", category="food")
    _pc, oc = _product("10", category="clothing")
    cust = _customer()
    # Buy food twice, clothing once.
    for _ in range(2):
        cart_svc.add_item(customer_id=cust.id, offer_id=of.id, qty=Decimal("1"))
        orders_svc.checkout(customer_id=cust.id, payment_mode="cash")
    cart_svc.add_item(customer_id=cust.id, offer_id=oc.id, qty=Decimal("1"))
    orders_svc.checkout(customer_id=cust.id, payment_mode="cash")

    cats = shop_svc.usual_categories(customer_id=cust.id)
    assert cats[0]["category"] == "food"
    assert all(c["fallback"] is False for c in cats)

    h = auth_header(client, email=cust.email)
    r = client.get("/commerce/usual-categories", headers=h)
    assert r.status_code == 200 and r.get_json()["items"][0]["category"] == "food"


def test_usual_categories_fallback_for_new_customer(client) -> None:
    # Seed platform history from another customer.
    _pf, of = _product("10", category="food")
    buyer = _customer()
    cart_svc.add_item(customer_id=buyer.id, offer_id=of.id, qty=Decimal("1"))
    orders_svc.checkout(customer_id=buyer.id, payment_mode="cash")

    fresh = _customer()
    cats = shop_svc.usual_categories(customer_id=fresh.id)
    assert cats and all(c["fallback"] is True for c in cats)

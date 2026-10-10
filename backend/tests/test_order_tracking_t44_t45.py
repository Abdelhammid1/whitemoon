"""T-44 — order-stage notifications; T-45 — customer self-credit (always-on bar)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select

from app.commerce.services import cart as cart_svc
from app.commerce.services import orders as orders_svc
from app.extensions import db
from app.identity.models import CustomerProfile
from app.inventory.services import offers as offers_svc
from app.inventory.services import products as products_svc
from app.notifications.models import Notification
from tests.helpers import auth_header, create_user


def _uniq(p: str) -> str:
    return f"{p}{uuid.uuid4().hex[:6]}@wm.eg"


def _place_order(customer_id: int):
    sup = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    prod = products_svc.create_product(sku=f"P-{uuid.uuid4().hex[:6]}", name_ar="صنف", category="food", created_by=1)
    offer = offers_svc.upsert_offer(supplier_id=sup.id, product_id=prod.id, unit_price=Decimal("100"))
    cart_svc.add_item(customer_id=customer_id, offer_id=offer.id, qty=Decimal("1"))
    return orders_svc.checkout(customer_id=customer_id, payment_mode="cash")


def test_order_stage_notifies_customer(client) -> None:
    cust = create_user(kind="customer", email=_uniq("cust"), roles=("customer",))
    db.session.add(CustomerProfile(user_id=cust.id, display_name="عميل"))
    db.session.commit()
    order = _place_order(cust.id)

    orders_svc.transition_order(order.id, "confirm")
    orders_svc.transition_order(order.id, "fulfill")

    notes = db.session.execute(
        select(Notification).where(
            Notification.user_id == cust.id, Notification.type == "order_stage"
        )
    ).scalars().all()
    assert len(notes) == 2  # confirmed + fulfilled


def test_my_credit_bar(client) -> None:
    cust = create_user(kind="customer", email=_uniq("cust"), roles=("customer",))
    db.session.add(CustomerProfile(user_id=cust.id, display_name="عميل"))
    db.session.commit()
    h = auth_header(client, email=cust.email)
    r = client.get("/credit/me", headers=h)
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body["tier"] in ("white", "green", "yellow", "red")
    # available = effective_limit - outstanding, all present.
    assert "available" in body and "effective_limit" in body and "outstanding" in body
    assert Decimal(body["available"]) == Decimal(body["effective_limit"]) - Decimal(body["outstanding"])


def test_my_credit_requires_auth(client) -> None:
    assert client.get("/credit/me").status_code == 401

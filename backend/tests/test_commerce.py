"""EPIC 1 — marketplace commerce (Phase 4). US-1.1, 1.2, 1.4, 1.5, 1.6 and the
non-negotiable: supplier identity never appears in customer-facing responses."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.accounting.models import Account, JournalLine
from app.commerce.services import cart as cart_svc
from app.commerce.services import catalog as catalog_svc
from app.commerce.services import orders as orders_svc
from app.commerce.services import rfq as rfq_svc
from app.common.errors import Conflict
from app.extensions import db
from app.inventory.models import Product, SupplierOffer
from app.inventory.services import offers as offers_svc
from app.inventory.services import products as products_svc
from tests.helpers import auth_header, create_user


def _setup_two_suppliers(category: str = "food", price_a="100", price_b="90"):
    product = products_svc.create_product(sku=f"P-{category}", name_ar="صنف", category=category, created_by=1)
    a = create_user(kind="supplier", email=f"sa-{category}@example.com", roles=("supplier",))
    b = create_user(kind="supplier", email=f"sb-{category}@example.com", roles=("supplier",))
    oa = offers_svc.upsert_offer(supplier_id=a.id, product_id=product.id, unit_price=Decimal(price_a))
    ob = offers_svc.upsert_offer(supplier_id=b.id, product_id=product.id, unit_price=Decimal(price_b))
    return product, (a, oa), (b, ob)


def test_catalog_get_product_hides_supplier(client) -> None:
    product, _a, _b = _setup_two_suppliers(price_a="100", price_b="90")
    item = catalog_svc.get_product(product.id)
    assert item is not None
    assert item["best_price"] == "90.0000"  # lowest active offer
    assert item["best_offer_id"] is not None
    assert "supplier_id" not in item and "supplier" not in item
    # No active offer / unknown product → not available.
    assert catalog_svc.get_product(999999) is None


# ---------------------------------------------------------------- US-1.1


def test_catalog_browse_hides_supplier(client) -> None:
    product, _, _ = _setup_two_suppliers()
    db.session.commit()
    items = catalog_svc.browse()
    assert len(items) == 1
    row = items[0]
    assert row["product_id"] == product.id
    assert row["best_price"] == "90.0000"
    assert "supplier_id" not in row
    assert "supplier" not in str(row).lower() or "supplier_id" not in row


def test_catalog_endpoint_no_supplier_field(client) -> None:
    _setup_two_suppliers()
    create_user(kind="customer", phone="+201000000300", roles=("customer",))
    headers = auth_header(client, phone="+201000000300")
    r = client.get("/catalog/products", headers=headers)
    assert r.status_code == 200
    body = r.get_json()
    for item in body["items"]:
        assert "supplier_id" not in item


# ---------------------------------------------------------------- US-1.6 price lock


def test_supplier_cannot_raise_locked_price(client) -> None:
    _, (a, oa), _ = _setup_two_suppliers(price_a="100")
    cust = create_user(kind="customer", email="c1@example.com", roles=("customer",))
    db.session.commit()
    cart_svc.add_item(customer_id=cust.id, offer_id=oa.id, qty=Decimal("5"))

    # Raising oa's price while a lock is live must fail.
    with pytest.raises(Conflict):
        offers_svc.upsert_offer(supplier_id=a.id, product_id=oa.product_id, unit_price=Decimal("120"))
    db.session.rollback()


def test_supplier_can_lower_and_lock_follows(client) -> None:
    _, (a, oa), _ = _setup_two_suppliers(price_a="100")
    cust = create_user(kind="customer", email="c2@example.com", roles=("customer",))
    db.session.commit()
    cart_svc.add_item(customer_id=cust.id, offer_id=oa.id, qty=Decimal("5"))

    # Lowering is allowed and lowers the live lock.
    offers_svc.upsert_offer(supplier_id=a.id, product_id=oa.product_id, unit_price=Decimal("80"))
    summary = cart_svc.serialize_cart(cust.id)
    item = summary["items"][0]
    assert item["locked_unit_price"] == "80.0000"


# ---------------------------------------------------------------- US-1.2 checkout


def test_multi_supplier_cart_checkout_splits_and_hides_supplier(client) -> None:
    _, (_a, oa), (_b, ob) = _setup_two_suppliers(price_a="100", price_b="90")
    cust = create_user(kind="customer", email="c3@example.com", roles=("customer",))
    db.session.commit()
    cart_svc.add_item(customer_id=cust.id, offer_id=oa.id, qty=Decimal("2"))
    cart_svc.add_item(customer_id=cust.id, offer_id=ob.id, qty=Decimal("3"))

    order = orders_svc.checkout(customer_id=cust.id, payment_mode="cash")
    db.session.refresh(order)
    # Two suppliers → two sub-orders.
    assert len(order.sub_orders) == 2
    # Customer view hides supplier entirely.
    cust_view = orders_svc.serialize_order(order, for_customer=True)
    assert "sub_orders" not in cust_view
    assert "supplier_id" not in str(cust_view)
    # cash total = 2*100 + 3*90 = 470
    assert order.total_cash == Decimal("470.0000")


def test_checkout_posts_cash_journal(client) -> None:
    _, (_a, oa), _ = _setup_two_suppliers(price_a="100")
    cust = create_user(kind="customer", email="c4@example.com", roles=("customer",))
    db.session.commit()
    cart_svc.add_item(customer_id=cust.id, offer_id=oa.id, qty=Decimal("2"))
    order = orders_svc.checkout(customer_id=cust.id, payment_mode="cash")
    assert order.journal_entry_id is not None
    debit = db.session.execute(
        select(Account.code).join(JournalLine, JournalLine.account_id == Account.id)
        .where(JournalLine.entry_id == order.journal_entry_id, JournalLine.debit > 0)
    ).scalar_one()
    assert debit == "1131"  # customer receivable cash


def test_checkout_deferred_creates_terms_and_spread(client) -> None:
    _, (_a, oa), _ = _setup_two_suppliers(price_a="100")
    cust = create_user(kind="customer", email="c5@example.com", roles=("customer",))
    db.session.commit()
    cart_svc.add_item(customer_id=cust.id, offer_id=oa.id, qty=Decimal("10"))  # cash=1000
    # Deferred terms are server-computed (10% markup placeholder) — not client input.
    order = orders_svc.checkout(customer_id=cust.id, payment_mode="deferred")
    assert order.total_cash == Decimal("1000.0000")
    assert order.total_deferred == Decimal("1100.0000")  # 1000 × 1.10
    from app.accounting.models import DeferredTerm
    term = db.session.execute(select(DeferredTerm).where(DeferredTerm.order_id == order.id)).scalar_one()
    assert term.deferred_price == Decimal("1100.0000")
    assert term.early_settlement_discount == Decimal("50.0000")  # spread 100 × 50%


def test_expired_lock_reverts_to_current_price(client) -> None:
    from datetime import UTC, datetime, timedelta

    from app.commerce.models import PriceLock

    _, (a, oa), _ = _setup_two_suppliers(price_a="100")
    cust = create_user(kind="customer", email="c6b@example.com", roles=("customer",))
    db.session.commit()
    cart_svc.add_item(customer_id=cust.id, offer_id=oa.id, qty=Decimal("4"))  # locked at 100

    # Expire the lock, then the supplier raises the price (allowed — no live lock).
    pl = db.session.execute(select(PriceLock)).scalars().one()
    pl.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.session.commit()
    offers_svc.upsert_offer(supplier_id=a.id, product_id=oa.product_id, unit_price=Decimal("130"))

    # Cart + checkout now use the live price (130), not the expired lock (100).
    summary = cart_svc.serialize_cart(cust.id)
    assert summary["items"][0]["locked_unit_price"] == "130.0000"
    order = orders_svc.checkout(customer_id=cust.id, payment_mode="cash")
    assert order.total_cash == Decimal("520.0000")  # 4 × 130


def test_checkout_uses_locked_price_after_cut(client) -> None:
    _, (a, oa), _ = _setup_two_suppliers(price_a="100")
    cust = create_user(kind="customer", email="c6@example.com", roles=("customer",))
    db.session.commit()
    cart_svc.add_item(customer_id=cust.id, offer_id=oa.id, qty=Decimal("4"))  # locked at 100
    offers_svc.upsert_offer(supplier_id=a.id, product_id=oa.product_id, unit_price=Decimal("70"))  # cut → lock→70
    order = orders_svc.checkout(customer_id=cust.id, payment_mode="cash")
    assert order.total_cash == Decimal("280.0000")  # 4 * 70


# ---------------------------------------------------------------- below MOQ


def test_add_below_moq_rejected(client) -> None:
    product = products_svc.create_product(sku="MOQ-1", name_ar="x", category="food", created_by=1)
    sup = create_user(kind="supplier", email="moq@example.com", roles=("supplier",))
    offer = offers_svc.upsert_offer(supplier_id=sup.id, product_id=product.id, unit_price=Decimal("10"), moq=Decimal("5"))
    cust = create_user(kind="customer", email="c7@example.com", roles=("customer",))
    db.session.commit()
    with pytest.raises(Exception):  # noqa: B017 — BadRequest below_moq
        cart_svc.add_item(customer_id=cust.id, offer_id=offer.id, qty=Decimal("2"))
    db.session.rollback()


# ---------------------------------------------------------------- US-1.5 hint


def test_lower_price_hint_without_identity(client) -> None:
    _, (a, _oa), (_b, _ob) = _setup_two_suppliers(price_a="100", price_b="90")
    db.session.commit()
    rows = offers_svc.list_offers_for_supplier(a.id)
    serialized = offers_svc.serialize_own(rows[0])
    assert serialized["lower_price_exists"] is True
    # No competitor identity or exact price leaked.
    assert "competitor" not in serialized
    assert "supplier" not in {k for k in serialized if k != "lower_price_exists"}


# ---------------------------------------------------------------- US-1.4 RFQ


def test_rfq_offers_hidden_from_initiator_visible_to_admin(client) -> None:
    product = products_svc.create_product(sku="RFQ-1", name_ar="x", category="clothing", created_by=1)
    customer = create_user(kind="customer", email="rfqc@example.com", roles=("customer",))
    sup = create_user(kind="supplier", email="rfqs@example.com", roles=("supplier",))
    db.session.commit()

    r = rfq_svc.create_rfq(initiator_user_id=customer.id, initiator_type="customer", product_id=product.id, qty=Decimal("100"))
    rfq_svc.submit_offer(rfq_id=r.id, supplier_id=sup.id, unit_price=Decimal("55"))

    # Initiator sees price but NOT supplier id.
    as_initiator = rfq_svc.list_offers(rfq_id=r.id, requester_id=customer.id, is_admin=False)
    assert len(as_initiator) == 1
    assert "supplier_id" not in as_initiator[0]
    assert as_initiator[0]["unit_price"] == "55.0000"

    # Admin sees supplier id.
    as_admin = rfq_svc.list_offers(rfq_id=r.id, requester_id=1, is_admin=True)
    assert as_admin[0]["supplier_id"] == sup.id


def test_cart_endpoint_hides_supplier(client) -> None:
    _, (_a, oa), _ = _setup_two_suppliers(price_a="100")
    create_user(kind="customer", phone="+201000000310", roles=("customer",))
    db.session.commit()
    headers = auth_header(client, phone="+201000000310")
    client.post("/commerce/cart/items", headers=headers, json={"offer_id": oa.id, "qty": "2"})
    r = client.get("/commerce/cart", headers=headers)
    assert r.status_code == 200
    assert "supplier_id" not in str(r.get_json())


_ = (Product, SupplierOffer)  # keep imports referenced

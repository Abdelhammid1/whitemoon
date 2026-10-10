"""T-30 — unified supplier product screen + best-price discount rule.

Two-sided: a supplier edits price/qty/discount from one screen; a discount that
does not beat every other supplier is rejected with the exact, leak-free
message; a lower one is accepted; the customer catalog still shows the lowest
price with no supplier identity."""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.common.errors import BadRequest
from app.extensions import db
from app.commerce.services import catalog as catalog_svc
from app.inventory.services import offers as offers_svc
from app.inventory.services import products as products_svc
from app.notifications.models import Notification
from tests.helpers import auth_header, create_user


def _uniq(p: str) -> str:
    return f"{p}{uuid.uuid4().hex[:6]}@wm.eg"


def _product(sku: str = "P-t30"):
    return products_svc.create_product(sku=f"{sku}-{uuid.uuid4().hex[:4]}", name_ar="صنف اختبار", category="food", created_by=1)


def test_unified_set_price_qty_discount(client) -> None:
    prod = _product()
    # A competing supplier sits at 90 so there's a platform price to beat.
    other = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    offers_svc.upsert_offer(supplier_id=other.id, product_id=prod.id, unit_price=Decimal("90"))

    sup = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    db.session.commit()
    h = auth_header(client, email=sup.email)

    # One call sets price + qty + a percent discount that beats 90 (100×12% = 88).
    r = client.put(
        f"/inventory/supplier/products/{prod.id}",
        json={
            "unit_price": "100", "on_hand": "50", "moq": "5", "is_active": True,
            "discount_kind": "percent", "discount_value": "12",
        },
        headers=h,
    )
    assert r.status_code == 200, r.get_json()

    # The unified view reflects both the offer and the quantity.
    v = client.get("/inventory/supplier/products", headers=h)
    assert v.status_code == 200
    row = next(x for x in v.get_json()["items"] if x["product_id"] == prod.id)
    assert row["on_hand"] == "50.0000"
    assert row["offer"]["effective_price"] == "88.0000"
    assert row["offer"]["discount_kind"] == "percent"


def test_discount_equal_to_competitor_rejected_no_leak(client) -> None:
    prod = _product()
    other = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    offers_svc.upsert_offer(supplier_id=other.id, product_id=prod.id, unit_price=Decimal("90"))
    sup = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    db.session.commit()
    h = auth_header(client, email=sup.email)

    # A discounted price EQUAL to 90 does not achieve best price → rejected.
    r = client.put(
        f"/inventory/supplier/products/{prod.id}",
        json={"unit_price": "100", "discount_kind": "price", "discount_value": "90"},
        headers=h,
    )
    assert r.status_code == 400
    body = r.get_json()
    assert body["message"] == offers_svc.REJECT_DISCOUNT_MSG
    # The message leaks neither a number nor a supplier.
    assert "90" not in body["message"] and str(other.id) not in body["message"]


def test_lower_discount_accepted(client) -> None:
    prod = _product()
    other = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    offers_svc.upsert_offer(supplier_id=other.id, product_id=prod.id, unit_price=Decimal("90"))
    sup = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    db.session.commit()
    h = auth_header(client, email=sup.email)

    r = client.put(
        f"/inventory/supplier/products/{prod.id}",
        json={"unit_price": "100", "discount_kind": "price", "discount_value": "85"},
        headers=h,
    )
    assert r.status_code == 200, r.get_json()


def test_catalog_shows_lowest_price_no_supplier(client) -> None:
    prod = _product()
    a = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    b = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    offers_svc.upsert_offer(supplier_id=a.id, product_id=prod.id, unit_price=Decimal("100"))
    # b discounts to 80 (beats 100) — the platform best becomes 80.
    offers_svc.upsert_offer(
        supplier_id=b.id, product_id=prod.id, unit_price=Decimal("100"),
        discount_kind="price", discount_value=Decimal("80"),
    )
    db.session.commit()

    item = catalog_svc.get_product(prod.id)
    assert item is not None
    # The discount is real: the customer-facing best price is the discounted 80,
    # and it points at b's (opaque) offer — with no supplier identity leaked.
    assert item["best_price"] == "80.0000"
    assert "supplier_id" not in item and "supplier" not in item


def test_non_best_discount_rejected_at_service() -> None:
    # Service-level guard: a discount equal to the only competitor is rejected.
    prod = _product()
    other = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    offers_svc.upsert_offer(supplier_id=other.id, product_id=prod.id, unit_price=Decimal("90"))
    sup = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    db.session.commit()
    try:
        offers_svc.upsert_offer(
            supplier_id=sup.id, product_id=prod.id, unit_price=Decimal("100"),
            discount_kind="price", discount_value=Decimal("95"),
        )
        raise AssertionError("expected BadRequest")
    except BadRequest as e:
        assert e.code == "discount_not_best"


def test_coding_request_notifies_admin(client) -> None:
    from sqlalchemy import select

    admin = create_user(kind="admin", email=_uniq("adm"), roles=("admin",))  # has product.manage
    sup = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    db.session.commit()
    h = auth_header(client, email=sup.email)
    r = client.post("/inventory/coding-requests", json={"name": "صنف جديد", "barcode": "6221"}, headers=h)
    assert r.status_code == 201, r.get_json()

    note = db.session.execute(
        select(Notification).where(
            Notification.user_id == admin.id, Notification.type == "coding_request"
        )
    ).scalar_one_or_none()
    assert note is not None

    mine = client.get("/inventory/coding-requests/mine", headers=h)
    assert mine.status_code == 200 and len(mine.get_json()["items"]) == 1

"""T-40 — inline price/stock edit, «نفد من عندي» pause, and bulk % adjust on
the supplier «منتجاتي» table."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.common.errors import BadRequest
from app.extensions import db
from app.inventory.services import offers as offers_svc
from app.inventory.services import products as products_svc
from tests.helpers import auth_header, create_user


def _uniq(p: str) -> str:
    return f"{p}{uuid.uuid4().hex[:6]}@wm.eg"


def _supplier():
    return create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))


def _product(name: str = "صنف"):
    return products_svc.create_product(
        sku=f"P-{uuid.uuid4().hex[:6]}", name_ar=name, category="food", created_by=1
    )


def test_patch_price_keeps_discount(client) -> None:
    sup = _supplier()
    p = _product()
    offers_svc.upsert_offer(
        supplier_id=sup.id, product_id=p.id, unit_price=Decimal("100"),
        discount_kind="percent", discount_value=Decimal("10"),
    )
    db.session.commit()
    out = offers_svc.patch_supplier_product(supplier_id=sup.id, product_id=p.id, unit_price=Decimal("120"))
    assert out["offer"]["unit_price"] == "120.0000"
    # The discount is untouched by an inline price edit.
    assert out["offer"]["discount_kind"] == "percent"
    assert out["offer"]["discount_value"] == "10.0000"


def test_patch_stock_only_without_offer(client) -> None:
    sup = _supplier()
    p = _product()
    # No offer — only stock exists; inline stock edit still works.
    out = offers_svc.patch_supplier_product(supplier_id=sup.id, product_id=p.id, on_hand=Decimal("42"))
    assert out["on_hand"] == "42.0000"
    assert out["offer"] is None


def test_patch_price_without_offer_rejected(client) -> None:
    sup = _supplier()
    p = _product()
    with pytest.raises(BadRequest) as e:
        offers_svc.patch_supplier_product(supplier_id=sup.id, product_id=p.id, unit_price=Decimal("50"))
    assert e.value.code == "no_offer"


def test_pause_and_resume(client) -> None:
    sup = _supplier()
    p = _product()
    offers_svc.upsert_offer(supplier_id=sup.id, product_id=p.id, unit_price=Decimal("100"))
    db.session.commit()
    paused = offers_svc.patch_supplier_product(supplier_id=sup.id, product_id=p.id, is_active=False)
    assert paused["offer"]["is_active"] is False
    resumed = offers_svc.patch_supplier_product(supplier_id=sup.id, product_id=p.id, is_active=True)
    assert resumed["offer"]["is_active"] is True


def test_bulk_adjust_increase_and_decrease(client) -> None:
    sup = _supplier()
    a, b = _product("أ"), _product("ب")
    offers_svc.upsert_offer(supplier_id=sup.id, product_id=a.id, unit_price=Decimal("100"))
    offers_svc.upsert_offer(supplier_id=sup.id, product_id=b.id, unit_price=Decimal("200"))
    db.session.commit()

    up = offers_svc.bulk_adjust_prices(
        supplier_id=sup.id, product_ids=[a.id, b.id], direction="increase", percent=Decimal("10")
    )
    assert up["updated"] == 2 and up["failed"] == []
    assert offers_svc._own_offer(sup.id, a.id).unit_price == Decimal("110.0000")
    assert offers_svc._own_offer(sup.id, b.id).unit_price == Decimal("220.0000")

    down = offers_svc.bulk_adjust_prices(
        supplier_id=sup.id, product_ids=[a.id], direction="decrease", percent=Decimal("50")
    )
    assert down["updated"] == 1
    assert offers_svc._own_offer(sup.id, a.id).unit_price == Decimal("55.0000")


def test_bulk_adjust_validates_percent(client) -> None:
    sup = _supplier()
    p = _product()
    offers_svc.upsert_offer(supplier_id=sup.id, product_id=p.id, unit_price=Decimal("100"))
    db.session.commit()
    with pytest.raises(BadRequest):
        offers_svc.bulk_adjust_prices(supplier_id=sup.id, product_ids=[p.id], direction="decrease", percent=Decimal("100"))
    with pytest.raises(BadRequest):
        offers_svc.bulk_adjust_prices(supplier_id=sup.id, product_ids=[p.id], direction="increase", percent=Decimal("0"))


def test_bulk_adjust_skips_product_without_offer(client) -> None:
    sup = _supplier()
    withoffer, nooffer = _product("أ"), _product("ب")
    offers_svc.upsert_offer(supplier_id=sup.id, product_id=withoffer.id, unit_price=Decimal("100"))
    db.session.commit()
    res = offers_svc.bulk_adjust_prices(
        supplier_id=sup.id, product_ids=[withoffer.id, nooffer.id], direction="increase", percent=Decimal("10")
    )
    assert res["updated"] == 1
    assert len(res["failed"]) == 1 and res["failed"][0]["product_id"] == nooffer.id


def test_inline_and_bulk_endpoints(client) -> None:
    sup = _supplier()
    p = _product()
    offers_svc.upsert_offer(supplier_id=sup.id, product_id=p.id, unit_price=Decimal("100"))
    db.session.commit()
    h = auth_header(client, email=sup.email)

    r = client.patch(f"/inventory/supplier/products/{p.id}", headers=h, json={"unit_price": "150"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["offer"]["unit_price"] == "150.0000"

    r = client.patch(f"/inventory/supplier/products/{p.id}", headers=h, json={"is_active": False})
    assert r.status_code == 200 and r.get_json()["offer"]["is_active"] is False

    r = client.post("/inventory/supplier/products/bulk-adjust", headers=h,
                     json={"product_ids": [p.id], "direction": "increase", "percent": "20"})
    assert r.status_code == 200 and r.get_json()["updated"] == 1
    # 150 * 1.20 = 180
    assert offers_svc._own_offer(sup.id, p.id).unit_price == Decimal("180.0000")

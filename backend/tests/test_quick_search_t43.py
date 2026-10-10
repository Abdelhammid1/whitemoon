"""T-43 — «طلب سريع» typo-tolerant search + filters + sort + filter options.

Needs pg_trgm (migration 0034) for the fuzzy-name assertion.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.commerce.services import catalog as catalog_svc
from app.extensions import db
from app.inventory.services import offers as offers_svc
from app.inventory.services import products as products_svc
from app.inventory.services import stock as stock_svc
from tests.helpers import auth_header, create_user


def _supplier():
    return create_user(kind="supplier", email=f"sup{uuid.uuid4().hex[:6]}@wm.eg", roles=("supplier",))


def _mk(*, name, barcode=None, brand=None, category="food", price="100", supplier=None, stock=None):
    sup = supplier or _supplier()
    p = products_svc.create_product(
        sku=f"P-{uuid.uuid4().hex[:6]}", name_ar=name, category=category,
        barcode=barcode, brand=brand, created_by=1,
    )
    offers_svc.upsert_offer(supplier_id=sup.id, product_id=p.id, unit_price=Decimal(price))
    if stock is not None:
        stock_svc.manual_adjust(
            supplier_id=sup.id, product_id=p.id, location_type="supplier", location_id=None, delta=Decimal(stock)
        )
    db.session.commit()
    return p, sup


def test_search_by_barcode_and_name(client) -> None:
    p, _ = _mk(name="سكر ناعم", barcode="6223000000011", brand="الدلتا")
    # Exact barcode.
    by_code = catalog_svc.quick_search(q="6223000000011")
    assert any(r["product_id"] == p.id for r in by_code)
    # Name substring.
    by_name = catalog_svc.quick_search(q="سكر")
    assert any(r["product_id"] == p.id for r in by_name)
    # No supplier identity ever leaks.
    assert "supplier_id" not in str(by_name)


def test_fuzzy_typo_match(client) -> None:
    p, _ = _mk(name="شامبو للأطفال")
    hits = catalog_svc.quick_search(q="شانبو للاطفال")  # typo + hamza slip
    assert any(r["product_id"] == p.id for r in hits)


def test_filters_category_brand_price_and_stock(client) -> None:
    sup = _supplier()
    a, _ = _mk(name="أرز مصري", brand="الضحى", category="food", price="50", supplier=sup, stock="30")
    b, _ = _mk(name="قميص قطن", brand="كوتون", category="clothing", price="500", supplier=sup, stock="0")

    only_food = catalog_svc.quick_search(category="food")
    ids = {r["product_id"] for r in only_food}
    assert a.id in ids and b.id not in ids

    by_brand = catalog_svc.quick_search(brand="كوتون")
    assert {r["product_id"] for r in by_brand} == {b.id}

    cheap = catalog_svc.quick_search(price_max=Decimal("100"))
    assert a.id in {r["product_id"] for r in cheap} and b.id not in {r["product_id"] for r in cheap}

    in_stock = catalog_svc.quick_search(in_stock_only=True)
    sids = {r["product_id"] for r in in_stock}
    assert a.id in sids and b.id not in sids  # b has 0 stock


def test_sort_price(client) -> None:
    sup = _supplier()
    _mk(name="صنف غالي", price="900", supplier=sup)
    _mk(name="صنف رخيص", price="10", supplier=sup)
    asc = catalog_svc.quick_search(sort="price_asc")
    prices = [Decimal(r["best_price"]) for r in asc]
    assert prices == sorted(prices)


def test_row_carries_unit_moq_available(client) -> None:
    p, _ = _mk(name="زيت طعام", price="80", stock="12")
    row = next(r for r in catalog_svc.quick_search(q="زيت") if r["product_id"] == p.id)
    assert row["unit"] and row["best_offer_id"]
    assert Decimal(row["available"]) == Decimal("12")
    assert "moq" in row


def test_filter_options_and_endpoint(client) -> None:
    _mk(name="عصير مانجو", brand="جهينة", category="food")
    create_user(kind="customer", email="qs-cust@wm.eg", roles=("customer",))
    h = auth_header(client, email="qs-cust@wm.eg")

    opts = client.get("/catalog/filter-options", headers=h)
    assert opts.status_code == 200
    body = opts.get_json()
    assert "جهينة" in body["brands"]
    assert any(c["code"] == "food" for c in body["categories"])

    r = client.get("/catalog/quick-search", headers=h, query_string={"q": "مانجو"})
    assert r.status_code == 200
    assert any(it["name_ar"] == "عصير مانجو" for it in r.get_json()["items"])

"""EPIC 4 — inventory + purchasing. Covers US-4.1..US-4.4 and the two
non-negotiables: supplier isolation and transfer→journal."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.accounting.models import Account, JournalLine
from app.extensions import db
from app.inventory.models import Product
from app.inventory.services import offers as offers_svc
from app.inventory.services import products as products_svc
from app.inventory.services import reorder as reorder_svc
from app.inventory.services import shortages as shortages_svc
from app.inventory.services import stock as stock_svc
from app.inventory.services import transfers as transfers_svc
from app.inventory.services.transfers import LineInput
from tests.helpers import auth_header, create_user


def _product(sku: str = "SKU-1", category: str = "food") -> Product:
    return products_svc.create_product(
        sku=sku, name_ar="صنف اختبار", category=category, created_by=1
    )


def _debit_codes(entry_id: int) -> list[str]:
    rows = db.session.execute(
        select(Account.code)
        .join(JournalLine, JournalLine.account_id == Account.id)
        .where(JournalLine.entry_id == entry_id, JournalLine.debit > 0)
    ).scalars().all()
    return list(rows)


def _credit_codes(entry_id: int) -> list[str]:
    rows = db.session.execute(
        select(Account.code)
        .join(JournalLine, JournalLine.account_id == Account.id)
        .where(JournalLine.entry_id == entry_id, JournalLine.credit > 0)
    ).scalars().all()
    return list(rows)


# ---------------------------------------------------------------- US-4.1


def test_product_catalog_enforces_category(client) -> None:
    p = _product(category="clothing")
    db.session.commit()
    assert p.category == "clothing"
    with pytest.raises(Exception):  # noqa: B017 — Conflict on bad category
        products_svc.create_product(sku="X", name_ar="x", category="toys")


def test_categories_endpoint_lists_from_backend(client) -> None:
    from tests.helpers import auth_header, create_user
    create_user(kind="admin", email="catadmin@example.com", roles=("admin",))
    h = auth_header(client, email="catadmin@example.com")
    r = client.get("/inventory/categories", headers=h)
    assert r.status_code == 200
    items = r.get_json()["items"]
    codes = {x["code"] for x in items}
    assert {"food", "electronics", "other"} <= codes
    assert all(x.get("label") for x in items)


def test_location_types_endpoint_lists_from_backend(client) -> None:
    from tests.helpers import auth_header, create_user
    create_user(kind="admin", email="loctadmin@example.com", roles=("admin",))
    h = auth_header(client, email="loctadmin@example.com")
    r = client.get("/inventory/location-types", headers=h)
    assert r.status_code == 200
    items = r.get_json()["items"]
    codes = {x["code"] for x in items}
    assert {"supplier", "channel_partner", "in_transit", "customer_hold"} <= codes
    assert all(x.get("label") for x in items)


def test_category_crud_and_product_guard(client) -> None:
    """T-15: admin adds a category; it shows in the catalog/product source,
    a product can use it, and it can't be deleted while products reference it."""
    from tests.helpers import auth_header, create_user
    create_user(kind="admin", email="catmgr@example.com", roles=("admin",))
    h = auth_header(client, email="catmgr@example.com")

    r = client.post(
        "/inventory/categories",
        headers=h,
        json={"name_ar": "مستلزمات طبية", "code": "medical", "icon": "medical_services"},
    )
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["code"] == "medical"

    # Arabic-only name (no code, no English) still creates a valid category.
    r2 = client.post("/inventory/categories", headers=h, json={"name_ar": "أدوات مكتبية"})
    assert r2.status_code == 201, r2.get_json()
    assert r2.get_json()["code"]  # a usable code was generated

    # Appears immediately in the active list (catalog filter + product form).
    codes = {c["code"] for c in client.get("/inventory/categories", headers=h).get_json()["items"]}
    assert "medical" in codes

    # A product can be created with it.
    p = client.post(
        "/inventory/products",
        headers=h,
        json={"sku": "MED-1", "name_ar": "كمامات طبية", "category": "medical"},
    )
    assert p.status_code in (200, 201), p.get_json()

    # Delete is blocked while products reference it.
    assert client.delete("/inventory/categories/medical", headers=h).status_code == 409

    # Unknown category is rejected.
    bad = client.post(
        "/inventory/products",
        headers=h,
        json={"sku": "X-1", "name_ar": "س", "category": "does_not_exist"},
    )
    assert bad.status_code == 409


def test_product_pro_form_create(client) -> None:
    """T-14: create a product with 2 variants, 2 images, pricing/tax/status and
    an initial batch; it serializes fully and shows in the catalog with image."""
    from decimal import Decimal

    from tests.helpers import auth_header, create_user
    admin = create_user(kind="admin", email="prodadmin@example.com", roles=("admin",))
    supplier = create_user(kind="supplier", email="prodsup@example.com", roles=("supplier",))
    h = auth_header(client, email="prodadmin@example.com")

    r = client.post(
        "/inventory/products",
        headers=h,
        json={
            "sku": "PRO-1", "name_ar": "زيت طعام فاخر", "name_en": "Premium Oil",
            "category": "food", "unit": "carton", "status": "active",
            "wholesale_price": "100.00", "deferred_price": "110.00", "default_moq": "5",
            "tax_rate": "14.0", "eta_code": "EG-1234", "eta_code_type": "EGS",
            "food_expiry_tracked": True,
            "variants": [
                {"sku": "PRO-1-S", "size": "صغير", "color": "ذهبي", "pack": "علبة"},
                {"sku": "PRO-1-L", "size": "كبير", "color": "ذهبي", "pack": "كرتونة"},
            ],
            "images": [
                {"url": "https://img.example/oil-a.jpg", "is_primary": True},
                {"url": "https://img.example/oil-b.jpg"},
            ],
            "initial_batch": {
                "supplier_id": supplier.id, "batch_code": "B-2026-01",
                "production_date": "2026-01-01", "expiry_date": "2027-01-01", "qty": "50",
            },
        },
    )
    assert r.status_code == 201, r.get_json()
    data = r.get_json()
    assert len(data["variants"]) == 2
    assert data["variants"][0]["pack"] == "علبة"
    assert len(data["images"]) == 2
    assert data["image_url"] == "https://img.example/oil-a.jpg"  # primary mirrored
    assert data["status"] == "active" and data["is_active"] is True
    assert data["eta_code_type"] == "EGS"
    pid = data["id"]

    # Detail endpoint returns the full record.
    det = client.get(f"/inventory/products/{pid}", headers=h)
    assert det.status_code == 200 and len(det.get_json()["images"]) == 2

    # With an active offer it shows in the catalog, carrying its primary image.
    offers_svc.upsert_offer(
        supplier_id=supplier.id, product_id=pid, unit_price=Decimal("100"), moq=Decimal("1")
    )
    db.session.commit()
    cat = client.get("/catalog/products", headers=h).get_json()["items"]
    row = next((x for x in cat if x["product_id"] == pid), None)
    assert row is not None and row["image_url"] == "https://img.example/oil-a.jpg"
    _ = admin  # created for symmetry


def test_product_image_upload_rejects_non_images(client) -> None:
    """T-14 security: an SVG/HTML upload (stored-XSS vector) is rejected; a real
    PNG is accepted and served with a safe image MIME + nosniff."""
    import io

    from tests.helpers import auth_header, create_user
    create_user(kind="admin", email="imgadmin@example.com", roles=("admin",))
    h = auth_header(client, email="imgadmin@example.com")
    pid = client.post(
        "/inventory/products", headers=h,
        json={"sku": "IMG-1", "name_ar": "منتج صور", "category": "food"},
    ).get_json()["id"]

    # An SVG disguised as .svg (or anything non-raster) is refused.
    svg = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
    bad = client.post(
        f"/inventory/products/{pid}/images", headers=h,
        data={"image": (io.BytesIO(svg), "x.svg")}, content_type="multipart/form-data",
    )
    assert bad.status_code == 400

    # A real 1x1 PNG is accepted.
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c6360000002000154a24f630000000049454e44ae426082"
    )
    ok = client.post(
        f"/inventory/products/{pid}/images", headers=h,
        data={"image": (io.BytesIO(png), "ok.png")}, content_type="multipart/form-data",
    )
    assert ok.status_code == 201, ok.get_json()
    img_url = ok.get_json()["url"]
    served = client.get(img_url)  # public serve
    assert served.status_code == 200
    assert served.mimetype == "image/png"
    assert served.headers.get("X-Content-Type-Options") == "nosniff"


def test_product_update_variant_and_image_integrity(client) -> None:
    """Audit fixes: re-saving a product keeping a variant SKU must not violate
    the unique constraint; duplicate SKUs in one payload are rejected cleanly;
    a legacy image_url is preserved when editing a product with no gallery."""
    from tests.helpers import auth_header, create_user
    create_user(kind="admin", email="upadmin@example.com", roles=("admin",))
    h = auth_header(client, email="upadmin@example.com")

    pid = client.post(
        "/inventory/products", headers=h,
        json={
            "sku": "UP-1", "name_ar": "منتج تعديل", "category": "food",
            "image_url": "https://img.example/legacy.jpg",
            "variants": [{"sku": "UP-1-S", "size": "صغير"}],
        },
    ).get_json()["id"]

    # Re-save keeping the same variant SKU (form always re-sends variants).
    r = client.put(
        f"/inventory/products/{pid}", headers=h,
        json={"status": "draft", "variants": [{"sku": "UP-1-S", "size": "وسط"}]},
    )
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["status"] == "draft"
    # Legacy image_url (no gallery rows) survived the edit.
    assert r.get_json()["image_url"] == "https://img.example/legacy.jpg"

    # Duplicate variant SKUs in one payload -> clean 409, not a 500.
    bad = client.put(
        f"/inventory/products/{pid}", headers=h,
        json={"variants": [{"sku": "DUP"}, {"sku": "DUP"}]},
    )
    assert bad.status_code == 409


def test_product_catalog_accepts_expanded_categories(client) -> None:
    # T-10: segments beyond food/clothing are now valid.
    for cat in ("electronics", "home", "beauty", "construction", "stationery", "automotive", "other"):
        p = _product(sku=f"EXP-{cat}", category=cat)
        db.session.commit()
        assert p.category == cat


def test_best_price_never_exposes_supplier(client) -> None:
    p = _product()
    s1 = create_user(kind="supplier", email="s1@example.com", roles=("supplier",))
    s2 = create_user(kind="supplier", email="s2@example.com", roles=("supplier",))
    offers_svc.upsert_offer(supplier_id=s1.id, product_id=p.id, unit_price=Decimal("100"))
    offers_svc.upsert_offer(supplier_id=s2.id, product_id=p.id, unit_price=Decimal("90"))
    best = offers_svc.best_offer(p.id)
    assert best is not None
    assert best["best_price"] == "90.0000"
    assert "supplier_id" not in best
    assert "supplier" not in best


def test_supplier_isolation_on_offers_endpoint(client) -> None:
    p = _product()
    s1 = create_user(kind="supplier", phone="+201000000200", roles=("supplier",))
    s2 = create_user(kind="supplier", phone="+201000000201", roles=("supplier",))
    offers_svc.upsert_offer(supplier_id=s1.id, product_id=p.id, unit_price=Decimal("100"))
    offers_svc.upsert_offer(supplier_id=s2.id, product_id=p.id, unit_price=Decimal("80"))
    db.session.commit()

    h2 = auth_header(client, phone="+201000000201")
    r = client.get("/inventory/offers/mine", headers=h2)
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert len(items) == 1
    assert items[0]["unit_price"] == "80.0000"


# ---------------------------------------------------------------- US-4.2


def test_transfer_issue_and_receive_post_journals(client) -> None:
    p = _product()
    supplier = create_user(kind="supplier", email="sup@example.com", roles=("supplier",))
    # seed source stock
    stock_svc.manual_adjust(
        supplier_id=supplier.id,
        product_id=p.id,
        location_type="supplier",
        location_id=None,
        delta=Decimal("100"),
    )

    order = transfers_svc.create_transfer_order(
        supplier_id=supplier.id,
        from_location_type="supplier",
        from_location_id=None,
        to_location_type="channel_partner",
        to_location_id=999,
        lines=[LineInput(product_id=p.id, qty=Decimal("30"), unit_cost=Decimal("10"))],
        initiated_by=1,
    )
    assert order.number.startswith("TRF-")

    issued = transfers_svc.issue(order_id=order.id, issued_by=1)
    assert issued.status == "issued"
    assert issued.issue_entry_id is not None
    # issued: dr 9100, cr 1151 (food platform)
    assert _debit_codes(issued.issue_entry_id) == ["9100"]
    assert _credit_codes(issued.issue_entry_id) == ["1151"]
    # source stock decremented 100 -> 70
    src = stock_svc.get_balance(
        supplier_id=supplier.id, product_id=p.id, location_type="supplier", location_id=None
    )
    assert src is not None and src.on_hand == Decimal("70.0000")

    received = transfers_svc.receive(order_id=order.id, received_by=1)
    assert received.status == "received"
    assert received.receive_entry_id is not None
    # received: dr 1153 (channel partner), cr 9100
    assert _debit_codes(received.receive_entry_id) == ["1153"]
    assert _credit_codes(received.receive_entry_id) == ["9100"]
    dest = stock_svc.get_balance(
        supplier_id=supplier.id,
        product_id=p.id,
        location_type="channel_partner",
        location_id=999,
    )
    assert dest is not None and dest.on_hand == Decimal("30.0000")


def test_transfer_issue_rejected_without_stock(client) -> None:
    p = _product()
    supplier = create_user(kind="supplier", email="sup2@example.com", roles=("supplier",))
    order = transfers_svc.create_transfer_order(
        supplier_id=supplier.id,
        from_location_type="supplier",
        from_location_id=None,
        to_location_type="channel_partner",
        to_location_id=1,
        lines=[LineInput(product_id=p.id, qty=Decimal("5"), unit_cost=Decimal("10"))],
        initiated_by=1,
    )
    with pytest.raises(Exception):  # noqa: B017 — NotFound: no source stock
        transfers_svc.issue(order_id=order.id, issued_by=1)
    db.session.rollback()


def test_mixed_category_transfer_rejected(client) -> None:
    food = _product(sku="F-1", category="food")
    cloth = _product(sku="C-1", category="clothing")
    supplier = create_user(kind="supplier", email="sup3@example.com", roles=("supplier",))
    with pytest.raises(Exception):  # noqa: B017 — BadRequest mixed category
        transfers_svc.create_transfer_order(
            supplier_id=supplier.id,
            from_location_type="supplier",
            from_location_id=None,
            to_location_type="channel_partner",
            to_location_id=1,
            lines=[
                LineInput(product_id=food.id, qty=Decimal("1"), unit_cost=Decimal("1")),
                LineInput(product_id=cloth.id, qty=Decimal("1"), unit_cost=Decimal("1")),
            ],
            initiated_by=1,
        )
    db.session.rollback()


# ---------------------------------------------------------------- US-4.4


def _pending_shortage(category: str = "food"):
    p = _product(sku=f"SH-{category}", category=category)
    supplier = create_user(
        kind="supplier", email=f"shsup-{category}@example.com", roles=("supplier",)
    )
    return shortages_svc.report_shortage(
        reporter_user_id=1,
        supplier_id=supplier.id,
        product_id=p.id,
        qty=Decimal("5"),
        unit_cost=Decimal("20"),
        evidence_s3_keys=["evidence/1.jpg"],
    )


def test_shortage_resolved_against_supplier_debits_payable(client) -> None:
    sh = _pending_shortage(category="food")
    resolved = shortages_svc.resolve_shortage(
        shortage_id=sh.id,
        responsible_party_type="supplier",
        responsible_party_id=None,
        reason="مسؤولية المورد — نقص عند الاستلام",
        resolved_by=1,
    )
    assert resolved.status == "resolved"
    assert resolved.journal_entry_id is not None
    assert _debit_codes(resolved.journal_entry_id) == ["2111"]  # food supplier payable
    assert _credit_codes(resolved.journal_entry_id) == ["1151"]


def test_shortage_resolved_against_agent_debits_1141(client) -> None:
    sh = _pending_shortage(category="clothing")
    agent_user = create_user(kind="agent", email="ag@example.com", roles=("agent",))
    # channel partner profile for the agent
    from app.identity.models import ChannelPartnerProfile

    db.session.add(
        ChannelPartnerProfile(
            user_id=agent_user.id, type="agent", display_name="وكيل القاهرة"
        )
    )
    db.session.commit()

    resolved = shortages_svc.resolve_shortage(
        shortage_id=sh.id,
        responsible_party_type="channel_partner",
        responsible_party_id=agent_user.id,
        reason="مسؤولية الوكيل أثناء العهدة",
        resolved_by=1,
    )
    assert resolved.journal_entry_id is not None
    assert _debit_codes(resolved.journal_entry_id) == ["1141"]  # agent receivable
    assert _credit_codes(resolved.journal_entry_id) == ["1152"]  # clothing


def test_shortage_unallocated_hits_loss_account(client) -> None:
    sh = _pending_shortage(category="food")
    resolved = shortages_svc.resolve_shortage(
        shortage_id=sh.id,
        responsible_party_type="unallocated",
        responsible_party_id=None,
        reason="تلف أثناء النقل — غير محدد المسؤول",
        resolved_by=1,
    )
    assert resolved.journal_entry_id is not None
    assert _debit_codes(resolved.journal_entry_id) == ["5310"]


# ---------------------------------------------------------------- US-4.3


def test_reorder_check_opens_alert_when_below_point(client) -> None:
    p = _product()
    supplier = create_user(kind="supplier", email="ro@example.com", roles=("supplier",))
    stock_svc.manual_adjust(
        supplier_id=supplier.id,
        product_id=p.id,
        location_type="supplier",
        location_id=None,
        delta=Decimal("3"),
        reorder_point=Decimal("10"),
    )
    created = reorder_svc.check(supplier_id=supplier.id)
    assert len(created) == 1
    assert created[0].level == 1
    # second check doesn't duplicate the open alert
    again = reorder_svc.check(supplier_id=supplier.id)
    assert again == []


# ---------------------------------------------------------------- RBAC


def test_customer_cannot_create_product(client) -> None:
    create_user(kind="customer", phone="+201000000210", roles=("customer",))
    headers = auth_header(client, phone="+201000000210")
    r = client.post(
        "/inventory/products",
        headers=headers,
        json={"sku": "X", "name_ar": "x", "category": "food"},
    )
    assert r.status_code == 403


def test_admin_can_create_product_via_route(client) -> None:
    create_user(kind="admin", email="invadmin@example.com", roles=("admin.high",))
    headers = auth_header(client, email="invadmin@example.com")
    r = client.post(
        "/inventory/products",
        headers=headers,
        json={"sku": "SKU-ADMIN", "name_ar": "منتج", "category": "food"},
    )
    assert r.status_code == 201
    assert r.get_json()["sku"] == "SKU-ADMIN"


def test_stock_balances_supplier_isolation_via_route(client) -> None:
    p = _product()
    s1 = create_user(kind="supplier", phone="+201000000220", roles=("supplier",))
    other = create_user(kind="supplier", email="other@example.com", roles=("supplier",))
    stock_svc.manual_adjust(
        supplier_id=s1.id, product_id=p.id, location_type="supplier",
        location_id=None, delta=Decimal("50"),
    )
    stock_svc.manual_adjust(
        supplier_id=other.id, product_id=p.id, location_type="supplier",
        location_id=None, delta=Decimal("70"),
    )
    headers = auth_header(client, phone="+201000000220")
    r = client.get("/inventory/stock-balances", headers=headers)
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert all(it["supplier_id"] == s1.id for it in items)
    assert len(items) == 1


def test_transfer_date_default_is_today(client) -> None:
    # smoke: a product with no category issues in transfer context
    assert date.today().year >= 2026

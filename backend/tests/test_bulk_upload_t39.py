"""T-39 — bulk price/qty/discount update by Excel: template, preview, apply."""

from __future__ import annotations

import io
import uuid
from decimal import Decimal

from openpyxl import Workbook

from app.extensions import db
from app.inventory.models import SupplierOffer
from app.inventory.services import bulk as bulk_svc
from app.inventory.services import offers as offers_svc
from app.inventory.services import products as products_svc
from tests.helpers import create_user

B1 = "4006381333931"  # valid EAN-13
B2 = "1234567890128"  # valid EAN-13
UNKNOWN = "0012345600009"  # valid check digit, no product


def _uniq(p: str) -> str:
    return f"{p}{uuid.uuid4().hex[:6]}@wm.eg"


def _book(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(bulk_svc.HEADERS)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _offer(product_id: int, supplier_id: int):
    return db.session.execute(
        SupplierOffer.__table__.select().where(
            (SupplierOffer.product_id == product_id) & (SupplierOffer.supplier_id == supplier_id)
        )
    ).first()


def _setup():
    sup = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    p1 = products_svc.create_product(sku=f"P-{uuid.uuid4().hex[:5]}", name_ar="صنف١", category="food", barcode=B1, created_by=1)
    p2 = products_svc.create_product(sku=f"P-{uuid.uuid4().hex[:5]}", name_ar="صنف٢", category="food", barcode=B2, created_by=1)
    offers_svc.upsert_offer(supplier_id=sup.id, product_id=p1.id, unit_price=Decimal("100"))
    db.session.commit()
    return sup, p1, p2


def test_template_and_export_are_xlsx(client) -> None:
    sup, _p1, _p2 = _setup()
    assert bulk_svc.template_bytes()[:2] == b"PK"  # xlsx = zip
    assert bulk_svc.export_bytes(sup.id)[:2] == b"PK"


def test_preview_classifies_rows_without_writing(client) -> None:
    sup, p1, _p2 = _setup()
    data = _book([
        [B1, "صنف١", 80, 60, 5, ""],      # green
        [UNKNOWN, "?", 10, 10, 0, ""],     # red — unknown barcode
        [B1, "صنف١", "", 0, 0, ""],         # red — price not positive
        [B2, "صنف٢", 50, 100, 0, "10%"],  # green — discount parsed
    ])
    res = bulk_svc.preview(supplier_id=sup.id, data=data)
    assert res["counts"]["green"] == 2
    assert res["counts"]["red"] == 2
    # Preview wrote nothing: p1's offer is still 100.
    offer = _offer(p1.id, sup.id)
    assert offer is not None and Decimal(str(offer.unit_price)) == Decimal("100.0000")


def test_apply_updates_only_valid_rows(client) -> None:
    sup, p1, p2 = _setup()
    data = _book([
        [B1, "صنف١", 80, 60, 5, ""],       # apply: price 60, qty 80
        [UNKNOWN, "?", 10, 10, 0, ""],      # skipped (red)
        [B2, "صنف٢", 50, 100, 0, "10%"],   # apply: new offer 100 with 10% discount
    ])
    res = bulk_svc.apply(supplier_id=sup.id, data=data)
    assert res["applied"] == 2
    assert res["total"] == 3

    o1 = _offer(p1.id, sup.id)
    assert o1 is not None and Decimal(str(o1.unit_price)) == Decimal("60.0000")
    o2 = _offer(p2.id, sup.id)
    assert o2 is not None and o2.discount_kind == "percent"


def test_bulk_endpoint_preview(client) -> None:
    from tests.helpers import auth_header

    sup, _p1, _p2 = _setup()
    data = _book([[B1, "صنف١", 80, 60, 5, ""]])
    h = auth_header(client, email=sup.email)
    r = client.post(
        "/inventory/supplier/products/bulk?mode=preview",
        data={"file": (io.BytesIO(data), "u.xlsx")},
        content_type="multipart/form-data",
        headers=h,
    )
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["counts"]["green"] == 1

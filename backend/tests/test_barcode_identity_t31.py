"""T-31 — barcode is the product's identity: check-digit validation, uniqueness,
auto WM internal code for local items, duplicate detection, and the admin
coding-request queue (create-from-request / reject)."""

from __future__ import annotations

import uuid

import pytest

from app.common.errors import BadRequest, Conflict
from app.extensions import db
from app.inventory.services import barcode as barcode_svc
from app.inventory.services import coding as coding_svc
from app.inventory.services import products as products_svc
from app.notifications.models import Notification
from tests.helpers import auth_header, create_user


def _uniq(p: str) -> str:
    return f"{p}{uuid.uuid4().hex[:6]}@wm.eg"


# A valid EAN-13 (check digit computed): 6221031492 -> use a known-valid code.
VALID_EAN13 = "4006381333931"  # textbook valid EAN-13
VALID_UPCA = "036000291452"    # textbook valid UPC-A


def test_barcode_validation() -> None:
    assert barcode_svc.is_valid_barcode(VALID_EAN13)
    assert barcode_svc.is_valid_barcode(VALID_UPCA)
    assert not barcode_svc.is_valid_barcode("4006381333930")  # wrong check digit
    assert not barcode_svc.is_valid_barcode("123")  # wrong length
    assert not barcode_svc.is_valid_barcode("abcdefabcdefg")  # non-digit
    with pytest.raises(BadRequest):
        barcode_svc.validate_barcode("4006381333930")


def test_local_product_gets_wm_code(client) -> None:
    p = products_svc.create_product(name_ar="صنف محلي", category="food", created_by=1)
    db.session.commit()
    assert p.sku == "WM-000001"
    p2 = products_svc.create_product(name_ar="صنف محلي ٢", category="food", created_by=1)
    db.session.commit()
    assert p2.sku == "WM-000002"


def test_barcoded_product_uses_barcode_identity(client) -> None:
    p = products_svc.create_product(name_ar="صنف عالمي", category="food", barcode=VALID_EAN13, created_by=1)
    db.session.commit()
    assert p.barcode == VALID_EAN13
    assert p.sku == VALID_EAN13  # barcode is the reference; no WM code generated


def test_duplicate_barcode_rejected(client) -> None:
    products_svc.create_product(name_ar="أول", category="food", barcode=VALID_EAN13, created_by=1)
    db.session.commit()
    with pytest.raises(Conflict) as e:
        products_svc.create_product(name_ar="ثانٍ", category="food", barcode=VALID_EAN13, created_by=1)
    assert e.value.code == "barcode_exists"


def test_invalid_barcode_rejected_on_create(client) -> None:
    with pytest.raises(BadRequest) as e:
        products_svc.create_product(name_ar="سيئ", category="food", barcode="4006381333930", created_by=1)
    assert e.value.code == "barcode_invalid"


def test_find_similar_warns(client) -> None:
    products_svc.create_product(name_ar="زيت عباد الشمس", category="food", created_by=1)
    db.session.commit()
    hits = products_svc.find_similar(name="زيت عباد")
    assert any("زيت عباد" in h["name_ar"] for h in hits)


def test_admin_queue_create_from_request_and_reject(client) -> None:
    admin = create_user(kind="admin", email=_uniq("adm"), roles=("admin",))  # product.manage
    sup = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    db.session.commit()

    # Supplier raises two coding requests.
    sh = auth_header(client, email=sup.email)
    r1 = client.post("/inventory/coding-requests", json={"name": "صنف للتكويد", "barcode": VALID_UPCA}, headers=sh)
    r2 = client.post("/inventory/coding-requests", json={"name": "صنف مرفوض"}, headers=sh)
    req1 = r1.get_json()["id"]
    req2 = r2.get_json()["id"]

    ah = auth_header(client, email=admin.email)
    # Admin sees the queue.
    q = client.get("/inventory/coding-requests?status=new", headers=ah)
    assert q.status_code == 200 and len(q.get_json()["items"]) == 2

    # Create a product FROM request 1 → request becomes coded + linked + supplier notified.
    cp = client.post("/inventory/products", json={
        "name_ar": "صنف للتكويد", "category": "food", "barcode": VALID_UPCA, "coding_request_id": req1,
    }, headers=ah)
    assert cp.status_code == 201, cp.get_json()
    pid = cp.get_json()["id"]
    coded = client.get("/inventory/coding-requests", headers=ah).get_json()["items"]
    row1 = next(x for x in coded if x["id"] == req1)
    assert row1["status"] == "coded" and row1["product_id"] == pid

    # Reject request 2 with a reason → supplier notified.
    rj = client.post(f"/inventory/coding-requests/{req2}/reject", json={"reason": "صنف مكرر"}, headers=ah)
    assert rj.status_code == 200 and rj.get_json()["status"] == "rejected"

    from sqlalchemy import select
    notes = db.session.execute(
        select(Notification).where(Notification.user_id == sup.id, Notification.type.in_(("coding_coded", "coding_rejected")))
    ).scalars().all()
    assert len(notes) == 2


def test_queue_requires_product_manage(client) -> None:
    sup = create_user(kind="supplier", email=_uniq("sup"), roles=("supplier",))
    h = auth_header(client, email=sup.email)
    assert client.get("/inventory/coding-requests", headers=h).status_code == 403

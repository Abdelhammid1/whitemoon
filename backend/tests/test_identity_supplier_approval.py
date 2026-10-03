"""Admin approve + reject supplier flows, with audit."""

from __future__ import annotations

from flask.testing import FlaskClient
from sqlalchemy import select

from app.audit.models import AuditEvent
from app.extensions import db
from app.identity.models import SupplierProfile
from tests.helpers import auth_header, create_user


def _register_pending_supplier(client: FlaskClient, phone: str) -> int:
    r = client.post(
        "/auth/register/supplier",
        json={
            "phone": phone,
            "password": "secret-pw-123",
            "legal_name": "Al-Fajr",
            "commercial_register_no": "CR-1",
            "tax_card_no": "TAX-1",
            "national_id": "1" * 14,
        },
    )
    body = r.get_json()
    v = client.post(
        "/auth/otp/verify",
        json={"user_id": body["user_id"], "code": body["otp"]["debug_code"]},
    )
    assert v.status_code == 200
    return int(body["user_id"])


def test_admin_approves_supplier(client: FlaskClient) -> None:
    create_user(kind="admin", email="a@example.com", roles=("admin",))
    headers = auth_header(client, email="a@example.com")

    sup_id = _register_pending_supplier(client, "+201000000030")
    r = client.post(f"/admin/suppliers/{sup_id}/approve", headers=headers)
    assert r.status_code == 200
    assert r.get_json()["status"] == "active"

    profile = db.session.get(SupplierProfile, sup_id)
    assert profile is not None
    assert profile.approval_status == "approved"
    assert profile.approved_at is not None

    events = db.session.execute(
        select(AuditEvent).where(AuditEvent.action == "supplier.approve")
    ).scalars().all()
    assert len(events) == 1
    assert events[0].target_id == str(sup_id)


def test_admin_rejects_supplier_with_reason(client: FlaskClient) -> None:
    create_user(kind="admin", email="a2@example.com", roles=("admin",))
    headers = auth_header(client, email="a2@example.com")

    sup_id = _register_pending_supplier(client, "+201000000031")
    r = client.post(
        f"/admin/suppliers/{sup_id}/reject",
        headers=headers,
        json={"reason": "Documents unclear — please resubmit"},
    )
    assert r.status_code == 200
    assert r.get_json()["status"] == "suspended"

    profile = db.session.get(SupplierProfile, sup_id)
    assert profile is not None
    assert profile.approval_status == "rejected"
    assert profile.rejection_reason is not None


def test_pending_suppliers_listing(client: FlaskClient) -> None:
    create_user(kind="admin", email="a3@example.com", roles=("admin",))
    headers = auth_header(client, email="a3@example.com")
    _register_pending_supplier(client, "+201000000032")
    _register_pending_supplier(client, "+201000000033")

    r = client.get("/admin/suppliers/pending", headers=headers)
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert len(items) == 2


def test_non_admin_cannot_approve(client: FlaskClient) -> None:
    create_user(kind="customer", phone="+201000000034", roles=("customer",))
    headers = auth_header(client, phone="+201000000034")
    sup_id = _register_pending_supplier(client, "+201000000035")

    r = client.post(f"/admin/suppliers/{sup_id}/approve", headers=headers)
    assert r.status_code == 403

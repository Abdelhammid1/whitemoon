"""Customer and supplier registration + OTP verification."""

from __future__ import annotations

from flask.testing import FlaskClient
from sqlalchemy import select

from app.audit.models import AuditEvent
from app.extensions import db
from app.identity.models import SupplierProfile, User


def test_customer_register_otp_activates_account(client: FlaskClient) -> None:
    r = client.post(
        "/auth/register/customer",
        json={
            "phone": "+201000000001",
            "password": "secret-pw-123",
            "display_name": "Ahmed",
        },
    )
    assert r.status_code == 201, r.get_json()
    body = r.get_json()
    assert body["status"] == "pending"
    assert body["otp"]["debug_code"] is not None  # console provider

    user_id = body["user_id"]
    code = body["otp"]["debug_code"]

    v = client.post("/auth/otp/verify", json={"user_id": user_id, "code": code})
    assert v.status_code == 200
    verified = v.get_json()
    assert verified["status"] == "active"
    assert verified["kind"] == "customer"


def test_supplier_register_stays_pending_after_otp(client: FlaskClient) -> None:
    r = client.post(
        "/auth/register/supplier",
        json={
            "phone": "+201000000002",
            "password": "secret-pw-123",
            "legal_name": "شركة الفجر للتوريدات",
            "commercial_register_no": "CR-12345",
            "tax_card_no": "TAX-98765",
            "national_id": "29800000000000",
        },
    )
    assert r.status_code == 201, r.get_json()
    body = r.get_json()
    user_id = body["user_id"]
    code = body["otp"]["debug_code"]

    v = client.post("/auth/otp/verify", json={"user_id": user_id, "code": code})
    assert v.status_code == 200
    verified = v.get_json()
    # OTP verified, but supplier must still be approved by admin.
    assert verified["status"] == "pending"
    assert verified["kind"] == "supplier"

    profile = db.session.get(SupplierProfile, user_id)
    assert profile is not None
    assert profile.approval_status == "pending"


def test_password_is_hashed_not_plaintext(client: FlaskClient) -> None:
    client.post(
        "/auth/register/customer",
        json={
            "phone": "+201000000003",
            "password": "very-secret-pw",
            "display_name": "Hany",
        },
    )
    user = db.session.execute(
        select(User).where(User.phone == "+201000000003")
    ).scalar_one()
    assert user.password_hash != "very-secret-pw"
    assert user.password_hash.startswith("$argon2")


def test_duplicate_phone_rejected(client: FlaskClient) -> None:
    base = {
        "phone": "+201000000004",
        "password": "secret-pw-123",
        "display_name": "x",
    }
    assert client.post("/auth/register/customer", json=base).status_code == 201
    r = client.post("/auth/register/customer", json=base)
    assert r.status_code == 409
    assert r.get_json()["error"] == "user_exists"


def test_bad_otp_rejected_and_counted(client: FlaskClient) -> None:
    r = client.post(
        "/auth/register/customer",
        json={
            "phone": "+201000000005",
            "password": "secret-pw-123",
            "display_name": "x",
        },
    )
    user_id = r.get_json()["user_id"]
    bad = client.post("/auth/otp/verify", json={"user_id": user_id, "code": "000000"})
    assert bad.status_code == 401
    assert bad.get_json()["error"] == "otp_mismatch"


def test_registration_emits_audit_event(client: FlaskClient) -> None:
    client.post(
        "/auth/register/customer",
        json={
            "phone": "+201000000006",
            "password": "secret-pw-123",
            "display_name": "x",
        },
    )
    events = db.session.execute(
        select(AuditEvent).where(AuditEvent.action == "user.register")
    ).scalars().all()
    assert len(events) == 1

"""Impersonation leaves a full audit trail; reasons are enforced."""

from __future__ import annotations

from flask.testing import FlaskClient
from sqlalchemy import select

from app.audit.models import AuditEvent
from app.extensions import db
from app.identity.models import ImpersonationGrant
from tests.helpers import auth_header, create_user


def test_impersonation_start_and_stop_audited(client: FlaskClient) -> None:
    high = create_user(kind="admin", email="h@example.com", roles=("admin.high",))
    target = create_user(
        kind="customer", phone="+201000000040", roles=("customer",)
    )

    headers = auth_header(client, email="h@example.com")
    start = client.post(
        "/admin/impersonate/start",
        headers=headers,
        json={"target_user_id": target.id, "reason": "Debug missing-order ticket #42"},
    )
    assert start.status_code == 200
    body = start.get_json()
    assert body["access_token"]
    assert body["acting_as_user_id"] == target.id
    assert body["admin_user_id"] == high.id

    grant_id = body["grant_id"]
    stop = client.post(f"/admin/impersonate/{grant_id}/stop", headers=headers)
    assert stop.status_code == 200

    grant = db.session.get(ImpersonationGrant, grant_id)
    assert grant is not None
    assert grant.revoked_at is not None

    actions = {
        e.action
        for e in db.session.execute(select(AuditEvent)).scalars().all()
    }
    assert "user.impersonate.start" in actions
    assert "user.impersonate.stop" in actions


def test_impersonation_requires_reason(client: FlaskClient) -> None:
    create_user(kind="admin", email="h2@example.com", roles=("admin.high",))
    target = create_user(
        kind="customer", phone="+201000000041", roles=("customer",)
    )
    headers = auth_header(client, email="h2@example.com")
    r = client.post(
        "/admin/impersonate/start",
        headers=headers,
        json={"target_user_id": target.id, "reason": "no"},
    )
    assert r.status_code == 400


def test_non_privileged_user_cannot_impersonate(client: FlaskClient) -> None:
    create_user(kind="customer", phone="+201000000042", roles=("customer",))
    target = create_user(
        kind="customer", phone="+201000000043", roles=("customer",)
    )
    headers = auth_header(client, phone="+201000000042")
    r = client.post(
        "/admin/impersonate/start",
        headers=headers,
        json={"target_user_id": target.id, "reason": "I just want to"},
    )
    assert r.status_code == 403

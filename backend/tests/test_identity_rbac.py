"""RBAC — @require_permission denies when the user lacks the code."""

from __future__ import annotations

from flask.testing import FlaskClient

from app.identity.services.rbac import get_user_permissions, has_permission
from tests.helpers import auth_header, create_user


def test_customer_cannot_hit_admin_list(client: FlaskClient) -> None:
    create_user(kind="customer", phone="+201000000020", roles=("customer",))
    headers = auth_header(client, phone="+201000000020")
    r = client.get("/admin/users", headers=headers)
    assert r.status_code == 403


def test_admin_can_hit_admin_list(client: FlaskClient) -> None:
    create_user(
        kind="admin", email="admin1@example.com", roles=("admin",)
    )
    headers = auth_header(client, email="admin1@example.com")
    r = client.get("/admin/users", headers=headers)
    assert r.status_code == 200


def test_wildcard_grants_everything(client: FlaskClient) -> None:
    high = create_user(
        kind="admin", email="high@example.com", roles=("admin.high",)
    )
    assert has_permission(high.id, "any.random.code")
    perms = get_user_permissions(high.id)
    assert "*" in perms


def test_unauth_request_rejected(client: FlaskClient) -> None:
    r = client.get("/admin/users")
    assert r.status_code == 401

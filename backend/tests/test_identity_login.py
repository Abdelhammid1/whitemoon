"""Login, logout, refresh, /auth/me."""

from __future__ import annotations

from flask.testing import FlaskClient

from tests.helpers import auth_header, create_user


def test_login_returns_access_and_refresh(client: FlaskClient) -> None:
    create_user(kind="customer", phone="+201000000010", roles=("customer",))

    r = client.post(
        "/auth/login",
        json={"phone": "+201000000010", "password": "secret-pw-123"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["requires_2fa"] is False


def test_login_wrong_password_rejected(client: FlaskClient) -> None:
    create_user(kind="customer", phone="+201000000011", roles=("customer",))
    r = client.post(
        "/auth/login",
        json={"phone": "+201000000011", "password": "nope"},
    )
    assert r.status_code == 401


def test_login_blocked_when_not_active(client: FlaskClient) -> None:
    create_user(
        kind="supplier", status="pending", phone="+201000000012", roles=("supplier",)
    )
    r = client.post(
        "/auth/login",
        json={"phone": "+201000000012", "password": "secret-pw-123"},
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "account_not_active"


def test_me_returns_identity(client: FlaskClient) -> None:
    create_user(kind="customer", phone="+201000000013", roles=("customer",))
    headers = auth_header(client, phone="+201000000013")
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    body = r.get_json()
    assert body["phone"] == "+201000000013"
    assert body["kind"] == "customer"


def test_logout_revokes_token(client: FlaskClient) -> None:
    create_user(kind="customer", phone="+201000000014", roles=("customer",))
    headers = auth_header(client, phone="+201000000014")
    assert client.post("/auth/logout", headers=headers).status_code == 200
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 401

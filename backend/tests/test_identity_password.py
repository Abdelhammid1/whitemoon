"""Self-service change-password (all users)."""

from __future__ import annotations

from tests.helpers import auth_header, create_user


def test_change_password_happy_path(client) -> None:
    create_user(kind="customer", phone="+201000055501", roles=("customer",))
    h = auth_header(client, phone="+201000055501")
    r = client.post(
        "/auth/change-password",
        json={"current_password": "secret-pw-123", "new_password": "BrandNew#2026"},
        headers=h,
    )
    assert r.status_code == 200, r.get_json()

    # old password no longer works; new one does
    assert client.post("/auth/login", json={"phone": "+201000055501", "password": "secret-pw-123"}).status_code == 401
    assert client.post("/auth/login", json={"phone": "+201000055501", "password": "BrandNew#2026"}).status_code == 200


def test_change_password_wrong_current_rejected(client) -> None:
    create_user(kind="customer", phone="+201000055502", roles=("customer",))
    h = auth_header(client, phone="+201000055502")
    r = client.post(
        "/auth/change-password",
        json={"current_password": "not-it", "new_password": "BrandNew#2026"},
        headers=h,
    )
    assert r.status_code == 401
    assert r.get_json()["error"] == "wrong_current_password"


def test_change_password_must_differ(client) -> None:
    create_user(kind="customer", phone="+201000055503", roles=("customer",))
    h = auth_header(client, phone="+201000055503")
    r = client.post(
        "/auth/change-password",
        json={"current_password": "secret-pw-123", "new_password": "secret-pw-123"},
        headers=h,
    )
    assert r.status_code == 400
    assert r.get_json()["error"] == "password_unchanged"


def test_change_password_min_length(client) -> None:
    create_user(kind="customer", phone="+201000055504", roles=("customer",))
    h = auth_header(client, phone="+201000055504")
    r = client.post(
        "/auth/change-password",
        json={"current_password": "secret-pw-123", "new_password": "short"},
        headers=h,
    )
    assert r.status_code == 400  # schema min_length=8


def test_change_password_requires_auth(client) -> None:
    assert client.post("/auth/change-password", json={"current_password": "x", "new_password": "yyyyyyyy"}).status_code == 401

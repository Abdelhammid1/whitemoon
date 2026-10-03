"""TOTP enrollment and 2FA-gated login for admin/agent."""

from __future__ import annotations

import pyotp
from flask.testing import FlaskClient

from tests.helpers import auth_header, create_user


def test_admin_enrolls_totp_then_logs_in_with_code(client: FlaskClient) -> None:
    create_user(kind="admin", email="t@example.com", roles=("admin",))

    # First login — admin not yet enrolled, so login succeeds without 2FA
    # (so the admin can reach the enrollment endpoint).
    headers = auth_header(client, email="t@example.com")

    start = client.post("/auth/2fa/enroll/start", headers=headers)
    assert start.status_code == 200
    secret = start.get_json()["secret"]
    assert secret
    assert start.get_json()["backup_codes"]

    totp = pyotp.TOTP(secret)
    finish = client.post(
        "/auth/2fa/enroll/finish",
        headers=headers,
        json={"code": totp.now()},
    )
    assert finish.status_code == 200

    # Now login without 2FA code returns requires_2fa=True.
    r_no = client.post(
        "/auth/login",
        json={"email": "t@example.com", "password": "secret-pw-123"},
    )
    assert r_no.status_code == 200
    body = r_no.get_json()
    assert body["requires_2fa"] is True
    assert "access_token" not in body

    # Login WITH valid TOTP succeeds.
    r_yes = client.post(
        "/auth/login",
        json={
            "email": "t@example.com",
            "password": "secret-pw-123",
            "totp_code": totp.now(),
        },
    )
    assert r_yes.status_code == 200
    assert r_yes.get_json()["access_token"]


def test_customer_login_does_not_require_2fa(client: FlaskClient) -> None:
    create_user(kind="customer", phone="+201000000050", roles=("customer",))
    r = client.post(
        "/auth/login",
        json={"phone": "+201000000050", "password": "secret-pw-123"},
    )
    assert r.get_json()["requires_2fa"] is False


def test_backup_code_works_once(client: FlaskClient) -> None:
    create_user(kind="admin", email="bc@example.com", roles=("admin",))
    headers = auth_header(client, email="bc@example.com")

    start = client.post("/auth/2fa/enroll/start", headers=headers)
    secret = start.get_json()["secret"]
    backup_codes = start.get_json()["backup_codes"]
    assert len(backup_codes) == 8

    client.post(
        "/auth/2fa/enroll/finish",
        headers=headers,
        json={"code": pyotp.TOTP(secret).now()},
    )

    first = backup_codes[0]
    r1 = client.post(
        "/auth/login",
        json={
            "email": "bc@example.com",
            "password": "secret-pw-123",
            "totp_code": first,
        },
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/auth/login",
        json={
            "email": "bc@example.com",
            "password": "secret-pw-123",
            "totp_code": first,
        },
    )
    assert r2.status_code == 401

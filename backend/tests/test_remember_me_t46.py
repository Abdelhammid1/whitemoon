"""T-46 — «تذكرني على هذا الجهاز»: remember-me eligibility, device listing,
revoke / revoke-all, change-password revocation, and the step-up helper."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.common.errors import Unauthorized
from app.extensions import db
from app.identity.models import Session
from app.identity.services import auth as auth_svc
from tests.helpers import create_user


def _login(client, email: str, remember: bool) -> dict:
    r = client.post(
        "/auth/login",
        json={"email": email, "password": "secret-pw-123", "remember_me": remember},
    )
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _auth(body: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {body['access_token']}"}


def test_customer_remember_me_creates_device(client) -> None:
    create_user(kind="customer", email="rm-c@wm.eg", roles=("customer",))
    body = _login(client, "rm-c@wm.eg", True)
    assert body["remembered"] is True
    devs = client.get("/auth/devices", headers=_auth(body)).get_json()["items"]
    assert len(devs) == 1
    assert "id" in devs[0] and "last_used_at" in devs[0]


def test_admin_excluded_from_remember(client) -> None:
    create_user(kind="admin", email="rm-a@wm.eg", roles=("admin.high",))
    body = _login(client, "rm-a@wm.eg", True)  # admin not TOTP-enrolled → tokens issue
    assert body["remembered"] is False
    assert client.get("/auth/devices", headers=_auth(body)).get_json()["items"] == []


def test_customer_without_remember_has_no_device(client) -> None:
    create_user(kind="customer", email="rm-c2@wm.eg", roles=("customer",))
    body = _login(client, "rm-c2@wm.eg", False)
    assert body["remembered"] is False
    assert client.get("/auth/devices", headers=_auth(body)).get_json()["items"] == []


def test_revoke_single_device(client) -> None:
    create_user(kind="supplier", email="rm-s@wm.eg", roles=("supplier",))
    body = _login(client, "rm-s@wm.eg", True)
    h = _auth(body)
    did = client.get("/auth/devices", headers=h).get_json()["items"][0]["id"]
    assert client.delete(f"/auth/devices/{did}", headers=h).status_code == 200
    assert client.get("/auth/devices", headers=h).get_json()["items"] == []


def test_revoke_all_devices(client) -> None:
    create_user(kind="customer", email="rm-c3@wm.eg", roles=("customer",))
    b1 = _login(client, "rm-c3@wm.eg", True)
    _login(client, "rm-c3@wm.eg", True)  # a second remembered device
    h = _auth(b1)
    assert len(client.get("/auth/devices", headers=h).get_json()["items"]) == 2
    r = client.delete("/auth/devices", headers=h)
    assert r.status_code == 200 and r.get_json()["count"] == 2
    assert client.get("/auth/devices", headers=h).get_json()["items"] == []


def test_change_password_revokes_remembered_devices(client) -> None:
    create_user(kind="customer", email="rm-c4@wm.eg", roles=("customer",))
    body = _login(client, "rm-c4@wm.eg", True)
    h = _auth(body)
    assert len(client.get("/auth/devices", headers=h).get_json()["items"]) == 1
    r = client.post(
        "/auth/change-password",
        headers=h,
        json={"current_password": "secret-pw-123", "new_password": "NewPass#2026"},
    )
    assert r.status_code == 200
    # The remembered refresh device was revoked; the current access token stays.
    assert client.get("/auth/devices", headers=h).get_json()["items"] == []


def test_remembered_session_has_long_expiry(client) -> None:
    u = create_user(kind="customer", email="rm-e@wm.eg", roles=("customer",))
    _login(client, "rm-e@wm.eg", True)
    s = db.session.execute(
        select(Session).where(
            Session.user_id == u.id, Session.kind == "refresh", Session.remembered.is_(True)
        )
    ).scalar_one()
    assert s.expires_at > datetime.now(UTC) + timedelta(days=25)


def test_revoke_device_cuts_off_that_device_access_now(client) -> None:
    create_user(kind="customer", email="rm-x@wm.eg", roles=("customer",))
    caller = _login(client, "rm-x@wm.eg", True)   # device 1 (the one doing the revoke)
    other = _login(client, "rm-x@wm.eg", True)    # device 2 (newest)
    h1, h2 = _auth(caller), _auth(other)
    # Newest-first: items[0] is device 2.
    did2 = client.get("/auth/devices", headers=h1).get_json()["items"][0]["id"]
    client.delete(f"/auth/devices/{did2}", headers=h1)
    # Device 2's live access token is blocklisted at once — not after TTL …
    assert client.get("/auth/me", headers=h2).status_code == 401
    # … while the caller stays signed in.
    assert client.get("/auth/me", headers=h1).status_code == 200


def test_revoke_all_keeps_caller_but_clears_devices(client) -> None:
    create_user(kind="customer", email="rm-y@wm.eg", roles=("customer",))
    b1 = _login(client, "rm-y@wm.eg", True)
    _login(client, "rm-y@wm.eg", True)  # a second device
    h = _auth(b1)
    assert client.delete("/auth/devices", headers=h).status_code == 200
    assert client.get("/auth/me", headers=h).status_code == 200  # caller kept
    assert client.get("/auth/devices", headers=h).get_json()["items"] == []


def test_verify_password_step_up(client) -> None:
    u = create_user(kind="customer", email="rm-v@wm.eg", roles=("customer",))
    auth_svc.verify_password_or_raise(u.id, "secret-pw-123")  # ok, no raise
    with pytest.raises(Unauthorized):
        auth_svc.verify_password_or_raise(u.id, "definitely-wrong")

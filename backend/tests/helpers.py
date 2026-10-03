"""Convenience helpers used across identity tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from flask.testing import FlaskClient
from sqlalchemy import select

from app.extensions import db
from app.identity.models import Role, User, UserRole
from app.identity.services import passwords


def create_user(
    *,
    kind: str,
    status: str = "active",
    phone: str | None = None,
    email: str | None = None,
    password: str = "secret-pw-123",
    roles: tuple[str, ...] = (),
) -> User:
    user = User(
        phone=phone,
        email=email,
        password_hash=passwords.hash_password(password),
        kind=kind,
        status=status,
        activated_at=datetime.now(UTC) if status == "active" else None,
    )
    db.session.add(user)
    db.session.flush()
    for role_code in roles:
        role_id = db.session.execute(
            select(Role.id).where(Role.code == role_code)
        ).scalar_one()
        db.session.add(UserRole(user_id=user.id, role_id=role_id))
    db.session.commit()
    return user


def login_body(**extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {"password": "secret-pw-123"}
    base.update(extra)
    return base


def auth_header(client: FlaskClient, *, phone: str | None = None,
                email: str | None = None, totp_code: str | None = None) -> dict[str, str]:
    body: dict[str, Any] = {"password": "secret-pw-123"}
    if phone:
        body["phone"] = phone
    if email:
        body["email"] = email
    if totp_code:
        body["totp_code"] = totp_code
    r = client.post("/auth/login", json=body)
    assert r.status_code == 200, r.get_json()
    token = r.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

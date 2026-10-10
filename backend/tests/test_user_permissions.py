"""Per-user permission delegation (Step 0)."""

from __future__ import annotations

from app.extensions import db
from app.identity.services.rbac import has_permission
from tests.helpers import auth_header, create_user


def test_direct_grant_makes_has_permission_true(client) -> None:
    staff = create_user(kind="staff", email="deleg@wm.eg", roles=("staff",))
    assert has_permission(staff.id, "deferred.settings.manage") is False

    admin = create_user(kind="admin", email="adm1@wm.eg", roles=("admin.high",))
    h = auth_header(client, email=admin.email)

    r = client.post(f"/admin/users/{staff.id}/permissions", json={"code": "deferred.settings.manage"}, headers=h)
    assert r.status_code == 200 and r.get_json()["granted"] is True
    db.session.expire_all()
    assert has_permission(staff.id, "deferred.settings.manage") is True

    # revoke reverses it
    r = client.delete(f"/admin/users/{staff.id}/permissions/deferred.settings.manage", headers=h)
    assert r.status_code == 200
    db.session.expire_all()
    assert has_permission(staff.id, "deferred.settings.manage") is False


def test_only_delegatable_codes_accepted(client) -> None:
    staff = create_user(kind="staff", email="deleg2@wm.eg", roles=("staff",))
    admin = create_user(kind="admin", email="adm2@wm.eg", roles=("admin.high",))
    h = auth_header(client, email=admin.email)
    r = client.post(f"/admin/users/{staff.id}/permissions", json={"code": "user.read"}, headers=h)
    assert r.status_code == 400 and r.get_json()["error"] == "not_delegatable"


def test_grant_requires_admin_high(client) -> None:
    staff = create_user(kind="staff", email="deleg3@wm.eg", roles=("staff",))
    plain = create_user(kind="admin", email="adm3@wm.eg", roles=("admin",))  # not admin.high
    h = auth_header(client, email=plain.email)
    r = client.post(f"/admin/users/{staff.id}/permissions", json={"code": "deferred.settings.manage"}, headers=h)
    assert r.status_code == 403

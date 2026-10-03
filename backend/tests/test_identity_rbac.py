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


def test_seed_rbac_revokes_stale_grant(client: FlaskClient) -> None:
    # A grant that is no longer declared in ROLE_PERMS must be pruned on the
    # next seed run (declarative reconcile, not add-only).
    from sqlalchemy import select

    from app.extensions import db
    from app.identity import seed as identity_seed
    from app.identity.models import Permission, Role, RolePermission

    staff = db.session.execute(select(Role).where(Role.code == "staff")).scalar_one()
    perm = db.session.execute(
        select(Permission).where(Permission.code == "credit.override")
    ).scalar_one()
    db.session.add(RolePermission(role_id=staff.id, permission_id=perm.id))
    db.session.commit()

    identity_seed.seed_rbac()  # reconcile

    still = db.session.execute(
        select(RolePermission).where(
            RolePermission.role_id == staff.id,
            RolePermission.permission_id == perm.id,
        )
    ).first()
    assert still is None

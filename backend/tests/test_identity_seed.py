"""seed.run() must survive multiple admins and stay idempotent (prod bug fix).

Regression: `seed_bootstrap_admin()` used `scalar_one_or_none()` on the
`admin.high` lookup, which raised `MultipleResultsFound` once a second admin
existed (the Users screen can add admins), aborting the whole seed including
`seed_rbac()`.
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.extensions import db
from app.identity import seed as identity_seed
from app.identity.models import Role, User, UserRole
from tests.helpers import create_user


def _admin_high_count() -> int:
    return db.session.execute(
        select(func.count())
        .select_from(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.code == "admin.high")
    ).scalar_one()


def test_seed_run_survives_multiple_admins_and_is_idempotent(client) -> None:
    # conftest already seeded one bootstrap admin.high; add a second so the old
    # equality query would have raised MultipleResultsFound.
    create_user(kind="admin", email="second.admin@wm.eg", roles=("admin.high",))
    before = _admin_high_count()
    assert before >= 2

    # Must not raise, and must not create a third admin.
    identity_seed.run()
    assert _admin_high_count() == before

    # Idempotent: a second run changes nothing either.
    identity_seed.run()
    assert _admin_high_count() == before


def test_seed_rbac_is_committed_before_admin_step(client) -> None:
    # Even if the admin step were to no-op (admins already present), RBAC must be
    # present and committed. Roles/permissions seeded in conftest remain intact.
    identity_seed.run()
    assert db.session.execute(
        select(Role).where(Role.code == "admin.high")
    ).scalar_one_or_none() is not None


def test_bootstrap_admin_skipped_when_any_admin_exists(client) -> None:
    # An existing admin (of any role) must block creating a default-password one.
    create_user(kind="admin", email="plain.admin@wm.eg", roles=("admin",))
    assert identity_seed.seed_bootstrap_admin() is None

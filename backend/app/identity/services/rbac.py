"""Role-based access control.

- `has_permission(user_id, code)` runs one indexed join.
- `@require_permission("supplier.approve")` on a Flask route rejects with
  403 if the current JWT subject lacks it.
- Supports a wildcard rule: a role carrying `*` grants everything (used only
  by the bootstrap `admin.high` role).
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import select

from ...common.errors import Forbidden
from ...extensions import db
from ..models import Permission, Role, RolePermission, UserPermission, UserRole


def has_permission(user_id: int, code: str) -> bool:
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id, Permission.code.in_([code, "*"]))
        .limit(1)
    )
    if db.session.execute(stmt).scalar_one_or_none() is not None:
        return True
    # Direct per-user grant (delegation), in addition to role grants.
    direct = select(UserPermission.id).where(
        UserPermission.user_id == user_id, UserPermission.permission_code == code
    ).limit(1)
    return db.session.execute(direct).scalar_one_or_none() is not None


def get_user_permissions(user_id: int) -> set[str]:
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .distinct()
    )
    perms = {row for row in db.session.execute(stmt).scalars().all()}
    direct = db.session.execute(
        select(UserPermission.permission_code).where(UserPermission.user_id == user_id)
    ).scalars().all()
    perms.update(direct)
    return perms


def users_with_permission(code: str) -> set[int]:
    """All user ids that hold `code` — through a role (including the `*`
    wildcard) or a direct per-user grant. Used to fan out notifications to
    everyone who can act on something (e.g. payment approvers)."""
    role_based = (
        select(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(Permission.code.in_([code, "*"]))
    )
    ids = set(db.session.execute(role_based).scalars().all())
    direct = select(UserPermission.user_id).where(UserPermission.permission_code == code)
    ids.update(db.session.execute(direct).scalars().all())
    return ids


def require_permission(code: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @jwt_required()
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            raw = get_jwt_identity()
            user_id = int(raw) if raw is not None else 0
            if not has_permission(user_id, code):
                raise Forbidden(
                    f"Missing permission: {code}", code="missing_permission"
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def assign_role(user_id: int, role_code: str) -> None:
    role_id = db.session.execute(
        select(Role.id).where(Role.code == role_code)
    ).scalar_one()
    exists = db.session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id, UserRole.role_id == role_id
        )
    ).first()
    if exists is None:
        db.session.add(UserRole(user_id=user_id, role_id=role_id))

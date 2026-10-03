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
from ..models import Permission, Role, RolePermission, UserRole


def has_permission(user_id: int, code: str) -> bool:
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id, Permission.code.in_([code, "*"]))
        .limit(1)
    )
    return db.session.execute(stmt).scalar_one_or_none() is not None


def get_user_permissions(user_id: int) -> set[str]:
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .distinct()
    )
    return {row for row in db.session.execute(stmt).scalars().all()}


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

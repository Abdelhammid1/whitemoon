"""Admin «إعدادات النظام» endpoints (T-37). Gated on `system.settings.manage`
(the admin.high `*` wildcard also satisfies it)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from ..common.errors import BadRequest
from ..identity.services.rbac import require_permission
from . import service

bp = Blueprint("system_settings", __name__, url_prefix="/admin/system-settings")

_PERM = "system.settings.manage"


def _uid() -> int | None:
    raw = get_jwt_identity()
    return int(raw) if raw is not None else None


@bp.get("")
@require_permission(_PERM)
def list_settings():
    return jsonify({"items": service.list_settings()})


@bp.get("/<key>/changes")
@require_permission(_PERM)
def setting_changes(key: str):
    return jsonify({"items": service.changes_for(key)})


@bp.patch("/<key>")
@require_permission(_PERM)
def update_setting(key: str):
    body = request.get_json(silent=True) or {}
    raw = body.get("value")
    if raw is None:
        raise BadRequest("value مطلوبة.", code="missing_value")
    view = service.set_value(key=key, raw=str(raw), actor_user_id=_uid())
    return jsonify(view)

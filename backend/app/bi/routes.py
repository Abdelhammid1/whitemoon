"""/bi blueprint — executive dashboard (read-only)."""

from __future__ import annotations

from flask import Blueprint, jsonify

from ..common.errors import ApiError
from ..identity.services.rbac import require_permission
from .services import bi as bi_svc

bp = Blueprint("bi", __name__, url_prefix="/bi")


@bp.get("/dashboard")
@require_permission("bi.view")
def dashboard():
    return jsonify(bi_svc.dashboard())


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

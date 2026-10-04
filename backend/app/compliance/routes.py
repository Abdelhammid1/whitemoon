"""/compliance blueprint — ETA readiness (EPIC 11)."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from pydantic import ValidationError

from ..common.errors import ApiError, BadRequest, Unauthorized
from ..identity.services.rbac import require_permission
from .schemas import SetEtaIn
from .services import compliance as svc

bp = Blueprint("compliance", __name__, url_prefix="/compliance")


def _parse(model_cls: Any) -> Any:
    try:
        return model_cls.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        raise BadRequest(f"Invalid payload: {e.errors()[0]['msg']}", code="validation_error") from e


def _uid() -> int:
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    return int(raw)


@bp.put("/products/<int:product_id>/eta")
@require_permission("product.manage")
def set_eta(product_id: int):
    p = _parse(SetEtaIn)
    product = svc.set_eta(
        product_id=product_id, eta_code=p.eta_code, eta_ready=p.eta_ready, actor_user_id=_uid()
    )
    return jsonify(svc.serialize_product_eta(product))


@bp.get("/eta-readiness")
@require_permission("product.manage")
def readiness():
    return jsonify(svc.readiness_report())


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

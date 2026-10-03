"""/production blueprint — manufacturing orders (EPIC 7).

All mutations require `production.manage` (internal production staff/admin).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from pydantic import ValidationError

from ..common.errors import ApiError, BadRequest, Unauthorized
from ..identity.services.rbac import require_permission
from .schemas import CompleteMOIn, CreateMOIn
from .services import production as svc
from .services.production import MaterialInput

bp = Blueprint("production", __name__, url_prefix="/production")


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


@bp.post("/orders")
@require_permission("production.manage")
def create_order():
    p = _parse(CreateMOIn)
    mo = svc.create_mo(
        owner_id=p.owner_id,
        output_product_id=p.output_product_id,
        output_qty=Decimal(str(p.output_qty)),
        materials=[
            MaterialInput(product_id=m.product_id, qty=Decimal(str(m.qty)), unit_cost=Decimal(str(m.unit_cost)))
            for m in p.materials
        ],
        stages=p.stages,
        location_type=p.location_type,
        location_id=p.location_id,
        actor_user_id=_uid(),
    )
    return jsonify(svc.serialize(mo)), 201


@bp.get("/orders/<int:mo_id>")
@require_permission("production.manage")
def get_order(mo_id: int):
    return jsonify(svc.serialize(svc.get_mo(mo_id)))


@bp.get("/orders")
@require_permission("production.manage")
def list_orders():
    owner = request.args.get("owner_id", type=int)
    return jsonify({"items": [svc.serialize(m) for m in svc.list_mos(owner_id=owner)]})


@bp.post("/orders/<int:mo_id>/advance")
@require_permission("production.manage")
def advance(mo_id: int):
    stage = svc.advance_stage(mo_id=mo_id, actor_user_id=_uid())
    return jsonify({"mo_id": mo_id, "stage_seq": stage.seq, "stage_status": stage.status})


@bp.post("/orders/<int:mo_id>/complete")
@require_permission("production.manage")
def complete(mo_id: int):
    p = _parse(CompleteMOIn)
    mo = svc.complete(mo_id=mo_id, posted_by=_uid(), entry_date=p.entry_date)
    return jsonify(svc.serialize(mo))


@bp.post("/orders/<int:mo_id>/cancel")
@require_permission("production.manage")
def cancel(mo_id: int):
    mo = svc.cancel(mo_id=mo_id, actor_user_id=_uid())
    return jsonify({"id": mo.id, "status": mo.status})


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

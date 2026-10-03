"""/credit blueprint — tiers, limits, overrides, dues, dunning (EPIC 5)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from pydantic import ValidationError
from sqlalchemy import select

from ..common.errors import ApiError, BadRequest, Unauthorized
from ..extensions import db
from ..identity.services.audit import emit as audit_emit
from ..identity.services.rbac import require_permission
from .models import EscalationEvent
from .schemas import FreezeIn, OverrideIn, PaymentIn
from .services import credit as credit_svc
from .services import escalation as esc_svc

bp = Blueprint("credit", __name__, url_prefix="/credit")


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


@bp.get("/customers/<int:customer_id>")
@require_permission("user.read")
def get_customer_credit(customer_id: int):
    return jsonify(credit_svc.serialize_tier(customer_id))


@bp.post("/customers/<int:customer_id>/recompute")
@require_permission("credit.manage")
def recompute(customer_id: int):
    credit_svc.recompute(customer_id)
    db.session.commit()
    return jsonify(credit_svc.serialize_tier(customer_id))


@bp.post("/overrides")
@require_permission("credit.override")
def create_override():
    payload = _parse(OverrideIn)
    uid = _uid()
    ov = credit_svc.set_override(
        customer_id=payload.customer_id,
        credit_limit=Decimal(str(payload.credit_limit)),
        reason=payload.reason,
        set_by=uid,
    )
    audit_emit("credit.override", actor_user_id=uid, target_type="customer", target_id=payload.customer_id, reason=payload.reason)
    return jsonify({"id": ov.id, "customer_id": ov.customer_id, "credit_limit": str(ov.credit_limit)}), 201


@bp.post("/dues/<int:due_id>/pay")
@require_permission("credit.manage")
def pay_due(due_id: int):
    payload = _parse(PaymentIn)
    due = credit_svc.record_payment(due_id=due_id, paid_on=payload.paid_on)
    audit_emit("credit.payment", actor_user_id=_uid(), target_type="due", target_id=due.id)
    return jsonify({"id": due.id, "status": due.status, "days_late": due.days_late})


@bp.post("/escalation/run")
@require_permission("credit.manage")
def run_escalation():
    n = esc_svc.run_all()
    return jsonify({"opened": n})


@bp.post("/customers/<int:customer_id>/freeze")
@require_permission("admin.high")
def freeze(customer_id: int):
    payload = _parse(FreezeIn)
    uid = _uid()
    ev = esc_svc.escalate_level5(customer_id=customer_id, reason=payload.reason, actor_user_id=uid)
    audit_emit("credit.freeze.level5", actor_user_id=uid, target_type="customer", target_id=customer_id, reason=payload.reason)
    return jsonify(esc_svc.serialize_event(ev)), 201


@bp.get("/customers/<int:customer_id>/escalations")
@require_permission("user.read")
def list_escalations(customer_id: int):
    rows = db.session.execute(
        select(EscalationEvent).where(EscalationEvent.customer_id == customer_id).order_by(EscalationEvent.id.desc())
    ).scalars().all()
    return jsonify({"items": [esc_svc.serialize_event(e) for e in rows]})


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

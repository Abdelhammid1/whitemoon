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
from ..identity.services.rbac import has_permission, require_permission
from .models import EscalationEvent
from .schemas import (
    CollectPaymentIn,
    FreezeIn,
    OverrideIn,
    PaymentIn,
    RejectPaymentIn,
    TierSettingIn,
)
from .services import credit as credit_svc
from .services import escalation as esc_svc
from .services import payments as pay_svc

bp = Blueprint("credit", __name__, url_prefix="/credit")


@bp.get("/tier-settings")
@require_permission("user.read")
def get_tier_settings():
    return jsonify({"items": credit_svc.all_tier_settings()})


@bp.put("/tier-settings/<tier>")
@require_permission("admin.high")
def put_tier_setting(tier: str):
    p = TierSettingIn.model_validate(request.get_json(silent=True) or {})
    row = credit_svc.set_tier_setting(tier=tier, credit_limit=p.credit_limit, deferred_pct=p.deferred_pct)
    audit_emit("credit.tier_setting.updated", actor_user_id=_uid(), target_type="credit_tier", target_id=row.tier)
    db.session.commit()
    return jsonify({"tier": row.tier, "credit_limit": str(row.credit_limit), "deferred_pct": str(row.deferred_pct)})


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


@bp.get("/dunning")
@require_permission("user.read")
def dunning():
    try:
        min_days = int(request.args.get("min_days", "0"))
    except ValueError:
        min_days = 0
    tier = request.args.get("tier")
    return jsonify({"items": credit_svc.dunning_list(min_days=min_days, tier=tier)})


@bp.get("/customers/<int:customer_id>/dues")
@require_permission("user.read")
def list_dues(customer_id: int):
    return jsonify({"items": [credit_svc.serialize_due(d) for d in credit_svc.list_dues(customer_id)]})


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


# ---------------------------------------------------------------- payments (T-02)


@bp.post("/payments/collect")
@require_permission("payment.collect")
def collect_payment():
    p = _parse(CollectPaymentIn)
    row = pay_svc.collect_payment(
        customer_id=p.customer_id,
        due_id=p.due_id,
        amount=p.amount,
        paid_on=p.paid_on,
        collected_by=_uid(),
    )
    return jsonify(pay_svc.serialize(row)), 201


@bp.get("/payments")
@require_permission("payment.collect")
def list_payments():
    uid = _uid()
    status = request.args.get("status")
    # Finance/admin see all; a partner/collector sees only what they collected.
    scope = None if has_permission(uid, "user.read") else uid
    rows = pay_svc.list_approvals(status=status, collected_by=scope)
    return jsonify({"items": [pay_svc.serialize(r) for r in rows]})


@bp.post("/payments/<int:approval_id>/approve")
@require_permission("payment.approve")
def approve_payment(approval_id: int):
    row = pay_svc.approve_payment(approval_id=approval_id, approver_id=_uid())
    return jsonify(pay_svc.serialize(row))


@bp.post("/payments/<int:approval_id>/reject")
@require_permission("payment.approve")
def reject_payment(approval_id: int):
    p = _parse(RejectPaymentIn)
    row = pay_svc.reject_payment(approval_id=approval_id, approver_id=_uid(), reason=p.reason)
    return jsonify(pay_svc.serialize(row))


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

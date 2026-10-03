"""/partners blueprint — deposits, terms, accruals, attribution (EPIC 6).

Financial mutations require `partner.manage` (finance/admin). Read endpoints
allow either `partner.manage` or the partner reading their own record.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from pydantic import ValidationError

from ..common.errors import ApiError, BadRequest, Forbidden, Unauthorized
from ..identity.services.rbac import has_permission, require_permission
from .schemas import AccrualIn, AttributeIn, DepositIn, RefundIn, TermsIn
from .services import partners as svc

bp = Blueprint("partners", __name__, url_prefix="/partners")


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


def _require_self_or_manage(partner_id: int) -> None:
    uid = _uid()
    if has_permission(uid, "partner.manage"):
        return
    if svc.is_partner_self(uid, partner_id):
        return
    raise Forbidden("غير مصرح", code="forbidden")


# ---------------------------------------------------------------- terms


@bp.get("/<int:partner_id>/terms")
def get_terms(partner_id: int):
    _require_self_or_manage(partner_id)
    return jsonify(svc.serialize_terms(svc.get_terms(partner_id)))


@bp.put("/<int:partner_id>/terms")
@require_permission("partner.manage")
def set_terms(partner_id: int):
    p = _parse(TermsIn)
    row = svc.set_terms(
        partner_id=partner_id,
        earns_commission=p.earns_commission,
        commission_rate_pct=Decimal(str(p.commission_rate_pct)),
        earns_investment_return=p.earns_investment_return,
        investment_return_rate_pct=Decimal(str(p.investment_return_rate_pct)),
        actor_user_id=_uid(),
    )
    return jsonify(svc.serialize_terms(row))


# ---------------------------------------------------------------- deposits


@bp.post("/<int:partner_id>/deposits")
@require_permission("partner.manage")
def record_deposit(partner_id: int):
    p = _parse(DepositIn)
    uid = _uid()
    dep = svc.record_deposit(
        partner_id=partner_id,
        amount=Decimal(str(p.amount)),
        deposit_date=p.deposit_date,
        recovery_conditions=p.recovery_conditions,
        posted_by=uid,
    )
    return jsonify(svc.serialize_deposit(dep)), 201


@bp.get("/<int:partner_id>/deposits")
def list_deposits(partner_id: int):
    _require_self_or_manage(partner_id)
    return jsonify({"items": [svc.serialize_deposit(d) for d in svc.list_deposits(partner_id)]})


@bp.post("/deposits/<int:deposit_id>/refund")
@require_permission("partner.manage")
def refund_deposit(deposit_id: int):
    p = _parse(RefundIn)
    uid = _uid()
    dep = svc.refund_deposit(deposit_id=deposit_id, reason=p.reason, posted_by=uid)
    return jsonify(svc.serialize_deposit(dep))


# ---------------------------------------------------------------- accruals


@bp.post("/<int:partner_id>/accruals")
@require_permission("partner.manage")
def compute_accrual(partner_id: int):
    p = _parse(AccrualIn)
    uid = _uid()
    row = svc.compute_accrual(
        partner_id=partner_id, kind=p.kind, year=p.year, month=p.month, posted_by=uid
    )
    return jsonify(svc.serialize_accrual(row)), 201


@bp.get("/<int:partner_id>/accruals")
def list_accruals(partner_id: int):
    _require_self_or_manage(partner_id)
    return jsonify({"items": [svc.serialize_accrual(a) for a in svc.list_accruals(partner_id)]})


@bp.get("/<int:partner_id>/accruals/statement")
def accrual_statement(partner_id: int):
    _require_self_or_manage(partner_id)
    kind = request.args.get("kind", "commission")
    if kind not in ("commission", "investment_return"):
        raise BadRequest("نوع الاستحقاق غير صالح", code="bad_accrual_kind")
    try:
        year = int(request.args["year"])
        month = int(request.args["month"])
    except (KeyError, ValueError) as e:
        raise BadRequest("year و month مطلوبان", code="period_required") from e
    return jsonify(svc.statement(partner_id, kind, year, month))


# ---------------------------------------------------------------- attribution


@bp.post("/orders/<int:order_id>/attribute")
@require_permission("partner.manage")
def attribute_order(order_id: int):
    p = _parse(AttributeIn)
    order = svc.attribute_order(order_id=order_id, partner_id=p.partner_id, actor_user_id=_uid())
    return jsonify({"order_id": order.id, "partner_id": order.partner_user_id})


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

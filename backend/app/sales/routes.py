"""/credit blueprint — tiers, limits, overrides, dues, dunning (EPIC 5)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from datetime import date

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError
from sqlalchemy import select

from ..accounting.providers import storage
from ..common.errors import ApiError, BadRequest, Forbidden, NotFound, Unauthorized
from ..common.images import IMAGE_EXTS, is_raster_image, mime_for_key
from ..extensions import db
from ..identity.services.audit import emit as audit_emit
from ..identity.services.rbac import has_permission, require_permission
from .models import EscalationEvent, PaymentApproval
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


@bp.get("/dues/mine")
@jwt_required()
def my_dues():
    """The caller's own OPEN dues, for the payment-upload due selector (T-29)."""
    return jsonify({"items": credit_svc.open_dues_for_customer(_uid())})


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
    # Finance/admin (user.read) see everything. An approver without user.read
    # (agent/branch) sees their own collections PLUS every customer-uploaded
    # receipt awaiting approval (T-29); a plain collector sees only their own.
    if has_permission(uid, "user.read"):
        rows = pay_svc.list_approvals(status=status)
    else:
        rows = pay_svc.list_approvals(
            status=status,
            collected_by=uid,
            include_customer_uploads=has_permission(uid, "payment.approve"),
        )
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


# ------------------------------------------------------------ customer receipts (T-21)


@bp.post("/payments/upload-receipt")
@jwt_required()
def upload_receipt():
    """A customer uploads a bank-transfer receipt (multipart `image`), optionally
    against a specific due. It is recorded as a *pending* approval that appears
    in the staff review queue (GET /credit/payments?status=pending)."""
    uid = _uid()
    if request.content_length and request.content_length > storage.MAX_UPLOAD_BYTES + 1024 * 1024:
        raise BadRequest("حجم الملف كبير جدًا (الحد ١٠ ميجابايت)", code="file_too_large")
    f = request.files.get("image")
    if f is None or not f.filename:
        raise BadRequest("مطلوب صورة إيصال التحويل", code="file_required")
    data = f.read(storage.MAX_UPLOAD_BYTES + 1)
    if not data:
        raise BadRequest("الملف فارغ", code="empty_file")
    if len(data) > storage.MAX_UPLOAD_BYTES:
        raise BadRequest("حجم الملف كبير جدًا (الحد ١٠ ميجابايت)", code="file_too_large")
    try:
        ext = storage.safe_extension(f.filename)
    except ValueError as e:
        raise BadRequest("نوع الملف غير مدعوم", code="bad_file_type") from e
    if ext not in IMAGE_EXTS or not is_raster_image(data):
        raise BadRequest("يُقبل فقط صورة (PNG أو JPG أو WEBP أو GIF)", code="bad_file_type")

    amount_raw = request.form.get("amount")
    if not amount_raw:
        raise BadRequest("مطلوب مبلغ التحويل", code="amount_required")
    try:
        amount = Decimal(amount_raw)
    except (ArithmeticError, ValueError) as e:
        raise BadRequest("مبلغ غير صالح", code="amount_invalid") from e
    due_id_raw = request.form.get("due_id")
    try:
        due_id = int(due_id_raw) if due_id_raw else None
    except ValueError as e:
        raise BadRequest("رقم ذمة غير صالح", code="due_id_invalid") from e
    paid_on_raw = request.form.get("paid_on")
    try:
        paid_on = date.fromisoformat(paid_on_raw) if paid_on_raw else date.today()
    except ValueError as e:
        raise BadRequest("تاريخ غير صالح (YYYY-MM-DD)", code="bad_date") from e

    # Same storage concern as accounting receipts → S3_BUCKET_RECEIPTS in prod.
    key = storage.store(data, prefix="receipts", ext=ext)
    try:
        row = pay_svc.upload_customer_receipt(
            customer_id=uid, due_id=due_id, amount=amount, paid_on=paid_on, receipt_key=key
        )
    except Exception:
        # Business validation (due ownership, amount, future date) failed after
        # the blob was written — roll it back so no orphaned file accumulates.
        storage.delete(key)
        raise
    return jsonify(pay_svc.serialize(row)), 201


@bp.get("/payments/mine")
@jwt_required()
def my_payments():
    """A customer's own submitted receipts / collected payments, newest first."""
    uid = _uid()
    rows = pay_svc.list_approvals(collected_by=uid)
    return jsonify({"items": [pay_svc.serialize(r) for r in rows]})


@bp.get("/payments/<int:approval_id>/receipt")
@jwt_required()
def payment_receipt(approval_id: int):
    """Stream a payment's receipt image. Visible to a finance reviewer
    (`payment.approve`) or to the customer who uploaded it — never by a
    client-supplied key."""
    uid = _uid()
    row = db.session.get(PaymentApproval, approval_id)
    if row is None or not row.receipt_key:
        raise NotFound("لا يوجد إيصال", code="receipt_not_found")
    # Finance reviewers see any receipt (the review queue); otherwise only the
    # customer who actually uploaded it — not merely anyone sharing customer_id.
    is_reviewer = has_permission(uid, "payment.approve")
    is_uploader = row.collected_by == uid and row.customer_id == uid
    if not is_reviewer and not is_uploader:
        raise Forbidden("غير مصرح", code="forbidden")
    blob = storage.load(row.receipt_key)
    if blob is None:
        raise NotFound("الصورة غير متاحة", code="image_unavailable")
    return Response(
        blob,
        mimetype=mime_for_key(row.receipt_key),
        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"},
    )


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

"""Supplier approval workflow.

Suppliers register and verify OTP but stay in `pending` status until an
admin with `supplier.approve` grants approval. Rejection requires a reason
and the user remains unable to log in. Both actions are audited.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ...common.errors import BadRequest, Conflict, NotFound
from ...extensions import db
from ..models import SupplierProfile, User
from . import audit

MIN_REASON_LEN = 5


def _notify_supplier(user_id: int, *, approved: bool, reason: str | None = None) -> None:
    """Tell the supplier their registration status (US-1.3). Approval is in-app
    (they can now log in); rejection goes by e-mail since they can't."""
    from ...notifications.services import notify as notify_svc

    if approved:
        notify_svc.notify(
            user_id=user_id,
            title="تم اعتماد حسابك",
            body="تم اعتماد تسجيلك كمورد — يمكنك الآن إضافة المنتجات والبيع.",
            type_="supplier_approval",
            channel="in_app",
        )
    else:
        notify_svc.notify(
            user_id=user_id,
            title="تم رفض طلب التسجيل",
            body=f"نأسف، تم رفض طلب تسجيلك كمورد. السبب: {reason}",
            type_="supplier_approval",
            channel="email",
        )


def approve(*, admin_user_id: int, user_id: int) -> User:
    user = db.session.get(User, user_id)
    if user is None or user.kind != "supplier":
        raise NotFound("Supplier not found", code="supplier_not_found")
    profile = db.session.get(SupplierProfile, user_id)
    if profile is None:
        raise NotFound("Profile missing", code="supplier_profile_missing")
    if profile.approval_status == "approved":
        raise Conflict("Already approved", code="already_approved")

    now = datetime.now(UTC)
    profile.approval_status = "approved"
    profile.approved_by = admin_user_id
    profile.approved_at = now
    profile.rejection_reason = None
    user.status = "active"
    user.activated_at = now
    audit.emit(
        "supplier.approve",
        actor_user_id=admin_user_id,
        target_type="user",
        target_id=user_id,
    )
    db.session.commit()
    _notify_supplier(user_id, approved=True)
    return user


def reject(*, admin_user_id: int, user_id: int, reason: str) -> User:
    if not reason or len(reason.strip()) < MIN_REASON_LEN:
        raise BadRequest("Reason required (≥5 chars)", code="reason_required")
    user = db.session.get(User, user_id)
    if user is None or user.kind != "supplier":
        raise NotFound("Supplier not found", code="supplier_not_found")
    profile = db.session.get(SupplierProfile, user_id)
    if profile is None:
        raise NotFound("Profile missing", code="supplier_profile_missing")

    profile.approval_status = "rejected"
    profile.rejection_reason = reason.strip()
    user.status = "suspended"
    audit.emit(
        "supplier.reject",
        actor_user_id=admin_user_id,
        target_type="user",
        target_id=user_id,
        reason=reason,
    )
    db.session.commit()
    _notify_supplier(user_id, approved=False, reason=reason.strip())
    return user

"""Single-level payment approval — EPIC 3/6, US-3.2b (T-02).

A payment collected by an agent/branch is recorded as *pending* and must be
approved by exactly one approver (the branch/agent manager) before it is
applied to the customer's due — no intermediate level. The collector may not
approve their own collection.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from ...common.errors import BadRequest, Conflict, Forbidden, NotFound
from ...common.money import to_money
from ...extensions import db
from ...identity.services.audit import emit as audit_emit
from ..models import CustomerDue, PaymentApproval
from . import credit as credit_svc


def _enforce_scope(user_id: int, customer_id: int) -> None:
    """A partner may only act on customers inside their own territory (T-01).
    Non-partners (staff/admin) are unaffected."""
    from ...partners.services import partners as partners_svc

    if partners_svc.is_partner(user_id) and not partners_svc.customer_in_scope(user_id, customer_id):
        raise Forbidden("العميل خارج نطاقك الجغرافي", code="out_of_scope")


def collect_payment(
    *, customer_id: int, due_id: int | None, amount: Decimal, paid_on: date, collected_by: int
) -> PaymentApproval:
    amount = to_money(amount)
    if amount <= 0:
        raise BadRequest("المبلغ يجب أن يكون موجبًا", code="amount_non_positive")
    if paid_on > datetime.now(credit_svc.BUSINESS_TZ).date():
        raise BadRequest("تاريخ السداد لا يمكن أن يكون في المستقبل", code="paid_on_future")
    _enforce_scope(collected_by, customer_id)
    if due_id is not None:
        due = db.session.get(CustomerDue, due_id)
        if due is None:
            raise NotFound("الذمة غير موجودة", code="due_not_found")
        if due.customer_id != customer_id:
            raise BadRequest("الذمة لا تخص هذا العميل", code="due_customer_mismatch")
        # No partial settlement in this version: the collected amount must
        # equal the due's full value (settling a due is all-or-nothing).
        if amount != to_money(due.amount):
            raise BadRequest(
                "لا يُقبل السداد الجزئي — المبلغ يجب أن يساوي قيمة الذمة",
                code="partial_payment_unsupported",
            )
    row = PaymentApproval(
        customer_id=customer_id,
        due_id=due_id,
        amount=amount,
        paid_on=paid_on,
        collected_by=collected_by,
        status="pending",
    )
    db.session.add(row)
    db.session.flush()
    audit_emit("payment.collected", actor_user_id=collected_by, target_type="payment_approval", target_id=row.id)
    db.session.commit()
    return row


def approve_payment(*, approval_id: int, approver_id: int) -> PaymentApproval:
    row = db.session.execute(
        select(PaymentApproval).where(PaymentApproval.id == approval_id).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise NotFound("طلب الاعتماد غير موجود", code="approval_not_found")
    if row.status != "pending":
        raise Conflict("الطلب لم يعد معلقًا", code="not_pending")
    # Exactly one level: the collector cannot approve their own collection.
    if approver_id == row.collected_by:
        raise Forbidden("لا يمكن اعتماد تحصيلك بنفسك", code="self_approval_forbidden")
    _enforce_scope(approver_id, row.customer_id)
    # Re-validate the due at approval time: still open and fully covered.
    if row.due_id is not None:
        due = db.session.get(CustomerDue, row.due_id)
        if due is None or due.status != "open":
            raise Conflict("الذمة لم تعد مفتوحة", code="due_not_open")
        if to_money(row.amount) != to_money(due.amount):
            raise BadRequest("المبلغ لا يطابق قيمة الذمة", code="amount_mismatch")
    row.status = "approved"
    row.approved_by = approver_id
    row.approved_at = datetime.now(UTC)
    audit_emit("payment.approved", actor_user_id=approver_id, target_type="payment_approval", target_id=row.id)
    db.session.flush()
    # Apply to the due now that it's approved (record_payment commits).
    if row.due_id is not None:
        credit_svc.record_payment(due_id=row.due_id, paid_on=row.paid_on)
    else:
        db.session.commit()
    return row


def reject_payment(*, approval_id: int, approver_id: int, reason: str) -> PaymentApproval:
    row = db.session.get(PaymentApproval, approval_id)
    if row is None:
        raise NotFound("طلب الاعتماد غير موجود", code="approval_not_found")
    if row.status != "pending":
        raise Conflict("الطلب لم يعد معلقًا", code="not_pending")
    _enforce_scope(approver_id, row.customer_id)
    row.status = "rejected"
    row.approved_by = approver_id
    row.approved_at = datetime.now(UTC)
    row.note = reason
    audit_emit("payment.rejected", actor_user_id=approver_id, target_type="payment_approval", target_id=row.id, reason=reason)
    db.session.commit()
    return row


def list_approvals(
    *, status: str | None = None, collected_by: int | None = None, limit: int = 100
) -> list[PaymentApproval]:
    stmt = select(PaymentApproval).order_by(PaymentApproval.id.desc()).limit(limit)
    if status:
        stmt = stmt.where(PaymentApproval.status == status)
    if collected_by is not None:
        stmt = stmt.where(PaymentApproval.collected_by == collected_by)
    return list(db.session.execute(stmt).scalars())


def serialize(row: PaymentApproval) -> dict[str, Any]:
    return {
        "id": row.id,
        "customer_id": row.customer_id,
        "due_id": row.due_id,
        "amount": str(row.amount),
        "paid_on": row.paid_on.isoformat(),
        "collected_by": row.collected_by,
        "status": row.status,
        "approved_by": row.approved_by,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
        "note": row.note,
    }

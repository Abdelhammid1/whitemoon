"""/accounting blueprint — manual journals, period mgmt, receipts, reports."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError
from sqlalchemy import select

from ..common.errors import ApiError, BadRequest, Unauthorized
from ..extensions import db
from ..identity.services.audit import emit as audit_emit
from ..identity.services.rbac import require_permission
from .models import Account, BankReceipt, DeferredTerm, Period
from .schemas import (
    AccountCreateIn,
    AccountUpdateIn,
    ApplyEarlyDiscountIn,
    DeferredTermsIn,
    ManualJournalIn,
    PeriodIn,
    ReceiptUploadIn,
    ReportFilterIn,
    ResolveReceiptIn,
)
from .services import deferred as deferred_svc
from .services import periods as periods_svc
from .services import receipts as receipts_svc
from .services import reports as reports_svc
from .services.events import LineInput, post_manual
from .services.reports import ReportFilter

bp = Blueprint("accounting", __name__, url_prefix="/accounting")


def _parse(model_cls: Any) -> Any:
    try:
        return model_cls.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        raise BadRequest(
            f"Invalid payload: {e.errors()[0]['msg']}",
            code="validation_error",
        ) from e


def _current_user_id() -> int:
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    return int(raw)


# ================================================================ read views
# Connect the frontend's accounting screens (chart, periods, receipts queue,
# deferred terms). All finance-gated reads.


@bp.get("/accounts")
@require_permission("period.close")
def list_accounts():
    rows = db.session.execute(select(Account).order_by(Account.code)).scalars().all()
    by_id = {a.id: a for a in rows}

    def parent_code(a: Account) -> str | None:
        parent = by_id.get(a.parent_id) if a.parent_id is not None else None
        return parent.code if parent is not None else None

    return jsonify(
        {
            "items": [
                {
                    "code": a.code,
                    "name_ar": a.name_ar,
                    "name_en": a.name_en,
                    "type": a.type,
                    "parent_code": parent_code(a),
                    "is_postable": a.is_postable,
                    "category": a.category,
                    "eta_code": a.eta_code,
                }
                for a in rows
            ]
        }
    )


@bp.post("/accounts")
@require_permission("admin.high")
def create_account():
    """Open a new account under an existing parent (T-09). The parent must
    exist (no account outside the approved tree); the child inherits the
    parent's type."""
    payload = _parse(AccountCreateIn)
    if db.session.execute(
        select(Account).where(Account.code == payload.code)
    ).scalar_one_or_none():
        raise BadRequest("الكود مستخدم بالفعل", code="account_code_taken")
    parent = db.session.execute(
        select(Account).where(Account.code == payload.parent_code)
    ).scalar_one_or_none()
    if parent is None:
        raise BadRequest(
            "الحساب الأب غير موجود — لا حساب خارج الشجرة المعتمدة",
            code="parent_not_found",
        )
    acc = Account(
        code=payload.code,
        name_ar=payload.name_ar,
        name_en=payload.name_en or payload.name_ar,
        type=parent.type,  # inherit — a child of assets is an asset
        parent_id=parent.id,
        is_postable=payload.is_postable,
        category=payload.category,
        eta_code=payload.eta_code,
    )
    db.session.add(acc)
    db.session.flush()
    audit_emit(
        "accounting.account.created",
        actor_user_id=_current_user_id(),
        target_type="account",
        target_id=acc.id,
        after={"code": acc.code, "type": acc.type, "parent": parent.code},
    )
    db.session.commit()
    return jsonify({"id": acc.id, "code": acc.code, "type": acc.type}), 201


@bp.put("/accounts/<code>")
@require_permission("admin.high")
def update_account(code: str):
    payload = _parse(AccountUpdateIn)
    acc = db.session.execute(
        select(Account).where(Account.code == code)
    ).scalar_one_or_none()
    if acc is None:
        raise BadRequest("الحساب غير موجود", code="account_not_found")
    if payload.name_ar is not None:
        acc.name_ar = payload.name_ar
    if payload.name_en is not None:
        acc.name_en = payload.name_en
    if payload.is_postable is not None:
        acc.is_postable = payload.is_postable
    if payload.category is not None:
        acc.category = payload.category
    if payload.eta_code is not None:
        acc.eta_code = payload.eta_code
    audit_emit(
        "accounting.account.updated",
        actor_user_id=_current_user_id(),
        target_type="account",
        target_id=acc.id,
    )
    db.session.commit()
    return jsonify({"id": acc.id, "code": acc.code})


@bp.get("/periods")
@require_permission("period.close")
def list_periods():
    year = request.args.get("year", type=int)
    stmt = select(Period).order_by(Period.year.desc(), Period.month.desc())
    if year:
        stmt = stmt.where(Period.year == year)
    rows = db.session.execute(stmt).scalars().all()
    return jsonify(
        {
            "items": [
                {
                    "id": p.id,
                    "year": p.year,
                    "month": p.month,
                    "starts_on": p.starts_on.isoformat(),
                    "ends_on": p.ends_on.isoformat(),
                    "is_closed": p.is_closed,
                    "closed_at": p.closed_at.isoformat() if p.closed_at else None,
                }
                for p in rows
            ]
        }
    )


@bp.get("/receipts")
@require_permission("period.close")
def list_receipts():
    status = request.args.get("status")
    stmt = select(BankReceipt).order_by(BankReceipt.id.desc()).limit(200)
    if status:
        stmt = stmt.where(BankReceipt.status == status)
    rows = db.session.execute(stmt).scalars().all()
    return jsonify(
        {
            "items": [
                {
                    "id": r.id,
                    "status": r.status,
                    "ocr_amount": str(r.ocr_amount) if r.ocr_amount is not None else None,
                    "ocr_reference": r.ocr_reference,
                    "matched_order_id": r.matched_order_id,
                    "manual_review_reason": r.manual_review_reason,
                    "uploaded_at": (
                        r.created_at.isoformat() if getattr(r, "created_at", None) else None
                    ),
                }
                for r in rows
            ]
        }
    )


@bp.get("/deferred-terms")
@require_permission("period.close")
def list_deferred_terms():
    rows = db.session.execute(
        select(DeferredTerm).order_by(DeferredTerm.id.desc()).limit(200)
    ).scalars().all()
    return jsonify(
        {
            "items": [
                {
                    "id": t.id,
                    "order_id": t.order_id,
                    "cash_price": str(t.cash_price),
                    "deferred_price": str(t.deferred_price),
                    "early_settlement_discount": str(t.early_settlement_discount),
                    "early_settlement_before": (
                        t.early_settlement_before.isoformat() if t.early_settlement_before else None
                    ),
                    "discount_applied": t.discount_applied,
                    "settled_at": t.settled_at.isoformat() if t.settled_at else None,
                }
                for t in rows
            ]
        }
    )


# ================================================================ periods


@bp.post("/periods/ensure")
@require_permission("period.close")
def period_ensure():
    payload = _parse(PeriodIn)
    period = periods_svc.ensure_period(year=payload.year, month=payload.month)
    return jsonify({"id": period.id, "year": period.year, "month": period.month})


@bp.post("/periods/close")
@require_permission("period.close")
def period_close():
    payload = _parse(PeriodIn)
    user_id = _current_user_id()
    period = periods_svc.close(
        year=payload.year, month=payload.month, closed_by=user_id
    )
    audit_emit(
        "accounting.period.close",
        actor_user_id=user_id,
        target_type="period",
        target_id=period.id,
    )
    return jsonify({"id": period.id, "is_closed": period.is_closed})


@bp.post("/periods/reopen")
@require_permission("period.reopen")
def period_reopen():
    payload = _parse(PeriodIn)
    user_id = _current_user_id()
    period = periods_svc.reopen(
        year=payload.year, month=payload.month, reopened_by=user_id
    )
    audit_emit(
        "accounting.period.reopen",
        actor_user_id=user_id,
        target_type="period",
        target_id=period.id,
        reason="period reopened",
    )
    return jsonify({"id": period.id, "is_closed": period.is_closed})


# ================================================================ manual journal


@bp.post("/journal/manual")
@require_permission("high.manual_journal")
def journal_manual():
    payload = _parse(ManualJournalIn)
    user_id = _current_user_id()

    # Closed-period override needs an extra permission check.
    if payload.allow_closed_period:
        from ..identity.services.rbac import has_permission
        if not has_permission(user_id, "high.manual_journal.closed_period"):
            raise BadRequest(
                "closed-period override requires permission "
                "high.manual_journal.closed_period",
                code="closed_period_override_denied",
            )

    lines = [
        LineInput(
            account_code=li.account_code,
            debit=Decimal(str(li.debit)),
            credit=Decimal(str(li.credit)),
            partner_type=li.partner_type,
            partner_id=li.partner_id,
            description=li.description,
        )
        for li in payload.lines
    ]
    result = post_manual(
        entry_date=payload.entry_date,
        description=payload.description,
        lines=lines,
        posted_by=user_id,
        reason=payload.reason,
        allow_closed_period=payload.allow_closed_period,
    )
    audit_emit(
        "accounting.journal.manual",
        actor_user_id=user_id,
        target_type="journal_entry",
        target_id=result.entry_id,
        reason=payload.reason,
    )
    return jsonify(
        {"entry_id": result.entry_id, "entry_no": result.entry_no}
    ), 201


# ================================================================ receipts (US-3.3)


@bp.post("/receipts/upload")
@jwt_required()
def receipt_upload():
    """Any authenticated user may upload a receipt for their own payment.
    No `@require_permission` — the identity gate is enough; audit happens.
    """
    user_id = _current_user_id()
    payload = _parse(ReceiptUploadIn)

    # Dev convenience: if the stub-OCR values were posted in the body,
    # prime the stub provider so `extract` returns them.
    if payload.ocr_stub_amount is not None or payload.ocr_stub_reference is not None:
        from .providers.ocr_provider import get_stub
        get_stub().prime(
            amount=payload.ocr_stub_amount,
            reference=payload.ocr_stub_reference,
        )

    result = receipts_svc.upload_and_match(
        uploaded_by=user_id,
        image_s3_key=payload.image_s3_key,
        image_bytes=b"",  # the real upload path reads bytes from S3
        expected_amount=payload.expected_amount,
        expected_reference=payload.expected_reference,
    )
    audit_emit(
        "accounting.receipt.upload",
        actor_user_id=user_id,
        target_type="receipt",
        target_id=result.receipt_id,
    )
    return jsonify(
        {
            "receipt_id": result.receipt_id,
            "status": result.status,
            "ocr_amount": str(result.ocr_amount) if result.ocr_amount else None,
            "ocr_reference": result.ocr_reference,
        }
    ), 201


@bp.post("/receipts/<int:receipt_id>/resolve")
@require_permission("period.close")  # finance role gate
def receipt_resolve(receipt_id: int):
    user_id = _current_user_id()
    payload = _parse(ResolveReceiptIn)
    receipt = receipts_svc.resolve_manual_review(
        receipt_id=receipt_id, status=payload.status, resolved_by=user_id
    )
    audit_emit(
        "accounting.receipt.resolve",
        actor_user_id=user_id,
        target_type="receipt",
        target_id=receipt.id,
        reason=f"status={payload.status}",
    )
    return jsonify({"receipt_id": receipt.id, "status": receipt.status})


# ================================================================ deferred terms (US-3.4)


@bp.post("/deferred-terms")
@require_permission("period.close")
def deferred_create():
    payload = _parse(DeferredTermsIn)
    user_id = _current_user_id()
    term = deferred_svc.create(
        order_id=payload.order_id,
        cash_price=Decimal(str(payload.cash_price)),
        deferred_price=Decimal(str(payload.deferred_price)),
        early_settlement_discount=Decimal(str(payload.early_settlement_discount)),
        early_settlement_before=payload.early_settlement_before,
    )
    audit_emit(
        "accounting.deferred.create",
        actor_user_id=user_id,
        target_type="deferred_term",
        target_id=term.id,
    )
    return jsonify(
        {
            "id": term.id,
            "order_id": term.order_id,
            "cash_price": str(term.cash_price),
            "deferred_price": str(term.deferred_price),
            "early_settlement_discount": str(term.early_settlement_discount),
            "early_settlement_before": term.early_settlement_before.isoformat()
            if term.early_settlement_before
            else None,
        }
    ), 201


@bp.post("/deferred-terms/apply-early-discount")
@require_permission("period.close")
def deferred_apply():
    payload = _parse(ApplyEarlyDiscountIn)
    user_id = _current_user_id()
    term = deferred_svc.apply_early_discount(
        order_id=payload.order_id, settled_on=payload.settled_on
    )
    audit_emit(
        "accounting.deferred.early_discount",
        actor_user_id=user_id,
        target_type="deferred_term",
        target_id=term.id,
    )
    return jsonify({"id": term.id, "discount_applied": term.discount_applied})


# ================================================================ reports


def _report_filter(payload: ReportFilterIn) -> ReportFilter:
    return ReportFilter(
        date_from=payload.date_from,
        date_to=payload.date_to,
        account_prefix=payload.account_prefix,
        partner_type=payload.partner_type,
        partner_id=payload.partner_id,
    )


@bp.post("/reports/trial-balance")
@require_permission("period.close")
def report_tb():
    payload = _parse(ReportFilterIn)
    return jsonify(reports_svc.trial_balance(_report_filter(payload)))


@bp.post("/reports/income-statement")
@require_permission("period.close")
def report_pl():
    payload = _parse(ReportFilterIn)
    return jsonify(reports_svc.income_statement(_report_filter(payload)))


@bp.post("/reports/balance-sheet")
@require_permission("period.close")
def report_bs():
    payload = _parse(ReportFilterIn)
    return jsonify(reports_svc.balance_sheet(_report_filter(payload)))


@bp.post("/reports/cash-flow")
@require_permission("period.close")
def report_cf():
    payload = _parse(ReportFilterIn)
    return jsonify(reports_svc.cash_flow(_report_filter(payload)))


@bp.get("/reports/general-ledger/<account_code>")
@require_permission("period.close")
def report_gl(account_code: str):
    df = date.fromisoformat(request.args["date_from"])
    dt = date.fromisoformat(request.args["date_to"])
    limit = int(request.args.get("limit", "500"))
    return jsonify(
        reports_svc.general_ledger(
            account_code=account_code,
            date_from=df,
            date_to=dt,
            limit=limit,
        )
    )


# ================================================================ errors


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

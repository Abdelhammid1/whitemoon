"""Channel-partner financial operations — EPIC 6.

Deposits (US-6.1), entitlement terms, and monthly commission / investment
-return accruals (US-6.2). Every money move posts a journal entry via the
event→journal map. Accrual amounts are SERVER-COMPUTED from realized sales in
the partner's scope — never client input (same discipline as deferred terms).
"""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select, text

from ...accounting.services import events as journal
from ...commerce.models import Order
from ...common.errors import BadRequest, Conflict, NotFound
from ...common.money import to_money
from ...extensions import db
from ...identity.models import ChannelPartnerProfile, CustomerProfile, User
from ...identity.services import passwords
from ...identity.services.audit import emit as audit_emit
from ...identity.services.rbac import assign_role
from ..models import PartnerAccrual, PartnerDeposit, PartnerTerms

# A sale counts toward a partner's accrual basis once it is realized —
# confirmed or fulfilled. Pending and cancelled orders never accrue.
REALIZED_ORDER_STATUSES = ("confirmed", "fulfilled")
MIN_REASON_LEN = 5

# Namespace for the per-partner advisory lock that serialises accrual
# computation (so the one-per-period check can't be raced into a double-post).
_PARTNER_LOCK_NS = 0x5052  # "PR"


def _now() -> datetime:
    return datetime.now(UTC)


def _lock_partner(partner_id: int) -> None:
    """Transaction-scoped advisory lock serialising a partner's financial
    mutations; held until the surrounding transaction commits."""
    db.session.execute(
        text("SELECT pg_advisory_xact_lock(:ns, :cid)"),
        {"ns": _PARTNER_LOCK_NS, "cid": partner_id},
    )


def _require_partner(partner_id: int) -> ChannelPartnerProfile:
    prof = db.session.get(ChannelPartnerProfile, partner_id)
    if prof is None:
        raise NotFound("ليس شريك قناة (وكيل/فرع)", code="not_a_partner")
    return prof


# ---------------------------------------------------------------- creation


def create_partner(
    *,
    type_: str,
    display_name: str,
    geo_scope: str | None,
    phone: str | None,
    email: str | None,
    password: str,
    earns_commission: bool,
    commission_rate_pct: Decimal,
    earns_investment_return: bool,
    investment_return_rate_pct: Decimal,
    actor_user_id: int,
) -> ChannelPartnerProfile:
    """Provision a new agent/branch: login user + profile + terms (T-08)."""
    if type_ not in ("agent", "branch"):
        raise BadRequest("النوع يجب أن يكون وكيل أو فرع", code="bad_partner_type")
    if not phone and not email:
        raise BadRequest("مطلوب هاتف أو بريد", code="identifier_required")
    if email and db.session.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise Conflict("البريد مستخدم بالفعل", code="email_taken")
    if phone and db.session.execute(select(User).where(User.phone == phone)).scalar_one_or_none():
        raise Conflict("الهاتف مستخدم بالفعل", code="phone_taken")

    user = User(
        phone=phone,
        email=email,
        password_hash=passwords.hash_password(password),
        kind=type_,
        status="active",
    )
    db.session.add(user)
    db.session.flush()
    prof = ChannelPartnerProfile(
        user_id=user.id, type=type_, display_name=display_name, geo_scope=geo_scope
    )
    db.session.add(prof)
    assign_role(user.id, type_)

    # A branch earns neither; an agent gets the terms as given.
    terms = PartnerTerms(partner_user_id=user.id)
    if type_ == "agent":
        terms.earns_commission = earns_commission
        terms.commission_rate_pct = commission_rate_pct if earns_commission else Decimal("0")
        terms.earns_investment_return = earns_investment_return
        terms.investment_return_rate_pct = (
            investment_return_rate_pct if earns_investment_return else Decimal("0")
        )
    db.session.add(terms)

    audit_emit(
        "partner.created",
        actor_user_id=actor_user_id,
        target_type="partner",
        target_id=user.id,
        after={"type": type_, "geo_scope": geo_scope},
    )
    db.session.commit()
    return prof


# ---------------------------------------------------------------- terms


def get_terms(partner_id: int) -> PartnerTerms:
    _require_partner(partner_id)
    row = db.session.get(PartnerTerms, partner_id)
    if row is None:
        row = PartnerTerms(partner_user_id=partner_id)
        db.session.add(row)
        db.session.flush()
    return row


def set_terms(
    *,
    partner_id: int,
    earns_commission: bool,
    commission_rate_pct: Decimal,
    earns_investment_return: bool,
    investment_return_rate_pct: Decimal,
    actor_user_id: int,
) -> PartnerTerms:
    prof = _require_partner(partner_id)
    # A branch is operationally distinct and earns neither (US-6.3).
    if prof.type == "branch" and (earns_commission or earns_investment_return):
        raise BadRequest(
            "الفرع لا يستحق عمولة أو عائدًا استثماريًا", code="branch_no_earnings"
        )
    row = get_terms(partner_id)
    row.earns_commission = earns_commission
    row.commission_rate_pct = commission_rate_pct if earns_commission else Decimal("0")
    row.earns_investment_return = earns_investment_return
    row.investment_return_rate_pct = (
        investment_return_rate_pct if earns_investment_return else Decimal("0")
    )
    audit_emit(
        "partner.terms.set",
        actor_user_id=actor_user_id,
        target_type="partner",
        target_id=partner_id,
    )
    db.session.commit()
    return row


# ---------------------------------------------------------------- deposits


def record_deposit(
    *,
    partner_id: int,
    amount: Decimal,
    deposit_date: date,
    recovery_conditions: str,
    posted_by: int,
) -> PartnerDeposit:
    _require_partner(partner_id)
    if len(recovery_conditions.strip()) < MIN_REASON_LEN:
        raise BadRequest("شروط الاسترداد إلزامية", code="recovery_conditions_required")
    amount = to_money(amount)
    if amount <= 0:
        raise BadRequest("المبلغ يجب أن يكون موجبًا", code="amount_non_positive")

    posting = journal.post(
        event_type="agent.deposit.received",
        entry_date=deposit_date,
        description=f"تأمين شريك #{partner_id}",
        context={"amount": amount, "partner_type": "agent", "partner_id": partner_id},
        posted_by=posted_by,
    )
    dep = PartnerDeposit(
        partner_user_id=partner_id,
        amount=amount,
        deposit_date=deposit_date,
        recovery_conditions=recovery_conditions.strip(),
        status="held",
        journal_entry_id=posting.entry_id,
    )
    db.session.add(dep)
    db.session.flush()
    audit_emit(
        "partner.deposit.received",
        actor_user_id=posted_by,
        target_type="partner_deposit",
        target_id=dep.id,
    )
    db.session.commit()
    return dep


def refund_deposit(*, deposit_id: int, reason: str, posted_by: int) -> PartnerDeposit:
    # Lock the row so two concurrent refunds can't both see 'held' and
    # double-post the reversal (double-spend).
    dep = db.session.execute(
        select(PartnerDeposit).where(PartnerDeposit.id == deposit_id).with_for_update()
    ).scalar_one_or_none()
    if dep is None:
        raise NotFound("التأمين غير موجود", code="deposit_not_found")
    if dep.status != "held":
        raise Conflict("التأمين لم يعد قائمًا", code="deposit_not_held")
    if len(reason.strip()) < MIN_REASON_LEN:
        raise BadRequest("السبب إلزامي (٥ أحرف فأكثر)", code="reason_required")

    posting = journal.post(
        event_type="agent.deposit.refunded",
        entry_date=_now().date(),
        description=f"رد تأمين شريك #{dep.partner_user_id}",
        context={
            "amount": to_money(dep.amount),
            "partner_type": "agent",
            "partner_id": dep.partner_user_id,
        },
        posted_by=posted_by,
    )
    dep.status = "refunded"
    dep.refunded_at = _now()
    dep.refund_reason = reason.strip()
    dep.refund_journal_entry_id = posting.entry_id
    audit_emit(
        "partner.deposit.refunded",
        actor_user_id=posted_by,
        target_type="partner_deposit",
        target_id=dep.id,
        reason=reason.strip(),
    )
    db.session.commit()
    return dep


def list_deposits(partner_id: int) -> list[PartnerDeposit]:
    return list(
        db.session.execute(
            select(PartnerDeposit)
            .where(PartnerDeposit.partner_user_id == partner_id)
            .order_by(PartnerDeposit.id.desc())
        ).scalars()
    )


# ---------------------------------------------------------------- accruals


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    if not (1 <= month <= 12):
        raise BadRequest("شهر غير صالح", code="bad_month")
    last_day = calendar.monthrange(year, month)[1]
    start = datetime(year, month, 1, tzinfo=UTC)
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)
    return start, end


def realized_sales(partner_id: int, year: int, month: int) -> tuple[Decimal, list[Order]]:
    """Sum of realized order value attributed to the partner in the month.
    Returns the basis and the contributing orders (for the statement)."""
    start, end = _month_bounds(year, month)
    orders = list(
        db.session.execute(
            select(Order)
            .where(
                Order.partner_user_id == partner_id,
                Order.status.in_(REALIZED_ORDER_STATUSES),
                Order.placed_at >= start,
                Order.placed_at <= end,
            )
            .order_by(Order.id)
        ).scalars()
    )
    basis = sum((to_money(o.total_cash) for o in orders), start=Decimal("0"))
    return basis, orders


def compute_accrual(
    *, partner_id: int, kind: str, year: int, month: int, posted_by: int
) -> PartnerAccrual:
    """Compute and post one monthly accrual. Idempotent per
    (partner, kind, year, month) — a second call for the same period is
    rejected rather than double-posting."""
    if kind not in ("commission", "investment_return"):
        raise BadRequest("نوع الاستحقاق غير صالح", code="bad_accrual_kind")
    _require_partner(partner_id)
    # Serialise concurrent computes for this partner so the one-per-period
    # check below can't be raced into a duplicate post (the unique constraint
    # is the final backstop).
    _lock_partner(partner_id)
    terms = get_terms(partner_id)

    if kind == "commission":
        if not terms.earns_commission:
            raise BadRequest("الشريك لا يستحق عمولة", code="not_entitled_commission")
        rate = to_money(terms.commission_rate_pct)
        event_type = "agent.commission.accrued"
    else:
        if not terms.earns_investment_return:
            raise BadRequest(
                "الشريك لا يستحق عائدًا استثماريًا", code="not_entitled_return"
            )
        rate = to_money(terms.investment_return_rate_pct)
        event_type = "agent.investment_return.accrued"

    existing = db.session.execute(
        select(PartnerAccrual).where(
            PartnerAccrual.partner_user_id == partner_id,
            PartnerAccrual.kind == kind,
            PartnerAccrual.period_year == year,
            PartnerAccrual.period_month == month,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise Conflict("الاستحقاق محتسب لهذه الفترة بالفعل", code="accrual_exists")

    basis, _orders = realized_sales(partner_id, year, month)
    amount = (basis * rate / Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    entry_id: int | None = None
    if amount > 0:
        posting = journal.post(
            event_type=event_type,
            entry_date=_month_bounds(year, month)[1].date(),
            description=f"{kind} شريك #{partner_id} — {year}/{month:02d}",
            context={"amount": amount, "partner_type": "agent", "partner_id": partner_id},
            posted_by=posted_by,
        )
        entry_id = posting.entry_id

    row = PartnerAccrual(
        partner_user_id=partner_id,
        kind=kind,
        period_year=year,
        period_month=month,
        basis_amount=basis,
        rate_pct=rate,
        amount=amount,
        computed_at=_now(),
        journal_entry_id=entry_id,
    )
    db.session.add(row)
    db.session.flush()
    audit_emit(
        "partner.accrual.computed",
        actor_user_id=posted_by,
        target_type="partner_accrual",
        target_id=row.id,
    )
    db.session.commit()
    return row


def list_accruals(partner_id: int) -> list[PartnerAccrual]:
    return list(
        db.session.execute(
            select(PartnerAccrual)
            .where(PartnerAccrual.partner_user_id == partner_id)
            .order_by(PartnerAccrual.id.desc())
        ).scalars()
    )


def statement(partner_id: int, kind: str, year: int, month: int) -> dict[str, Any]:
    """The detailed basis behind an accrual (US-6.2 acceptance)."""
    terms = get_terms(partner_id)
    rate = (
        terms.commission_rate_pct
        if kind == "commission"
        else terms.investment_return_rate_pct
    )
    basis, orders = realized_sales(partner_id, year, month)
    amount = (to_money(basis) * to_money(rate) / Decimal("100")).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    return {
        "partner_id": partner_id,
        "kind": kind,
        "period": f"{year}/{month:02d}",
        "rate_pct": str(rate),
        "basis_amount": str(to_money(basis)),
        "accrual_amount": str(amount),
        "orders": [
            {"id": o.id, "number": o.number, "total_cash": str(o.total_cash)}
            for o in orders
        ],
    }


# ---------------------------------------------------------------- attribution


def attribute_order(*, order_id: int, partner_id: int, actor_user_id: int) -> Order:
    """Attribute a realized sale to the agent/branch whose scope it falls in
    (feeds the accrual basis). Admin action."""
    order = db.session.get(Order, order_id)
    if order is None:
        raise NotFound("الطلب غير موجود", code="order_not_found")
    _require_partner(partner_id)
    order.partner_user_id = partner_id
    audit_emit(
        "partner.order.attributed",
        actor_user_id=actor_user_id,
        target_type="order",
        target_id=order_id,
    )
    db.session.commit()
    return order


# ---------------------------------------------------------------- serializers


def serialize_partner(p: ChannelPartnerProfile) -> dict[str, Any]:
    return {
        "partner_id": p.user_id,
        "type": p.type,
        "display_name": p.display_name,
        "geo_scope": p.geo_scope,
    }


def list_partners(type_: str | None = None) -> list[ChannelPartnerProfile]:
    stmt = select(ChannelPartnerProfile).order_by(ChannelPartnerProfile.user_id)
    if type_:
        stmt = stmt.where(ChannelPartnerProfile.type == type_)
    return list(db.session.execute(stmt).scalars())


def serialize_terms(t: PartnerTerms) -> dict[str, Any]:
    return {
        "partner_id": t.partner_user_id,
        "earns_commission": t.earns_commission,
        "commission_rate_pct": str(t.commission_rate_pct),
        "earns_investment_return": t.earns_investment_return,
        "investment_return_rate_pct": str(t.investment_return_rate_pct),
    }


def serialize_deposit(d: PartnerDeposit) -> dict[str, Any]:
    return {
        "id": d.id,
        "partner_id": d.partner_user_id,
        "amount": str(d.amount),
        "deposit_date": d.deposit_date.isoformat(),
        "recovery_conditions": d.recovery_conditions,
        "status": d.status,
        "refunded_at": d.refunded_at.isoformat() if d.refunded_at else None,
    }


def serialize_accrual(a: PartnerAccrual) -> dict[str, Any]:
    return {
        "id": a.id,
        "partner_id": a.partner_user_id,
        "kind": a.kind,
        "period": f"{a.period_year}/{a.period_month:02d}",
        "basis_amount": str(a.basis_amount),
        "rate_pct": str(a.rate_pct),
        "amount": str(a.amount),
        "computed_at": a.computed_at.isoformat(),
    }


def is_partner(user_id: int) -> bool:
    return db.session.get(ChannelPartnerProfile, user_id) is not None


def customer_in_scope(partner_user_id: int, customer_id: int) -> bool:
    """True when the customer's geo_area matches the partner's geo_scope
    (T-01). A partner with no scope, or a customer with no area, is out of
    scope — access is denied rather than leaked."""
    prof = db.session.get(ChannelPartnerProfile, partner_user_id)
    if prof is None or not prof.geo_scope:
        return False
    cp = db.session.get(CustomerProfile, customer_id)
    if cp is None or not cp.geo_area:
        return False
    return cp.geo_area.strip() == prof.geo_scope.strip()


def is_partner_self(user_id: int, partner_id: int) -> bool:
    return (
        user_id == partner_id
        and db.session.get(ChannelPartnerProfile, partner_id) is not None
    )

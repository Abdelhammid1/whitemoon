"""Flexible deferred-pricing engine (T-28).

Replaces the hardcoded flat markup with a configurable **annual** rate plus a
chosen duration, so the fee is transparent and proportional:

    fee   = round(amount × annual_pct / 100 / 365 × days, 2)
    total = amount + fee

The rate is resolved most-specific first: a per-customer exception → the
customer's colour-tier rate → the general rate. A red-tier customer may not
defer at all (consistent with the credit rules), so the resolver returns None.

All business values live in `sales.deferred_settings` / `deferred_tier_rates` /
`deferred_customer_exceptions` — editable from the admin UI, never code
constants. Suggested defaults are seeded `reviewed=False` until an authorised
admin confirms them.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select

from ...common.errors import BadRequest, NotFound
from ...common.money import to_money
from ...extensions import db
from ..models import DeferredCustomerException, DeferredSetting, DeferredTierRate

_TIERS = ("white", "green", "yellow", "red")
_FEE_SCALE = Decimal("0.01")  # the customer-facing fee is shown/charged to 2 dp

# Suggested (UNREVIEWED) defaults — see docs/help/T-28. General & white 36%/yr,
# green 30%, yellow 42%, red not allowed; durations 7/10/15/20/30, default 15,
# max 60. Finance must confirm these before go-live (the yellow banner).
_DEFAULT_GENERAL = Decimal("36")
_DEFAULT_TIER_RATES: dict[str, Decimal | None] = {
    "white": Decimal("36"),
    "green": Decimal("30"),
    "yellow": Decimal("42"),
    "red": None,  # red cannot defer
}
_DEFAULT_ALLOWED_DAYS = [7, 10, 15, 20, 30]
_DEFAULT_DAYS = 15
_DEFAULT_MAX_DAYS = 60


# ---------------------------------------------------------------- settings access


def get_settings() -> DeferredSetting:
    """The single settings row, seeding the suggested defaults on first access."""
    row = db.session.get(DeferredSetting, 1)
    if row is None:
        row = DeferredSetting(
            id=1,
            annual_pct_general=_DEFAULT_GENERAL,
            default_days=_DEFAULT_DAYS,
            max_days=_DEFAULT_MAX_DAYS,
            allowed_days=list(_DEFAULT_ALLOWED_DAYS),
            reviewed=False,
        )
        db.session.add(row)
        db.session.flush()
    return row


def seed_defaults() -> None:
    """Idempotently seed the settings row + per-tier rates (unreviewed)."""
    get_settings()
    for tier in _TIERS:
        if db.session.get(DeferredTierRate, tier) is None:
            db.session.add(DeferredTierRate(tier=tier, annual_pct=_DEFAULT_TIER_RATES[tier]))
    db.session.flush()


def _tier_rate(tier: str) -> Decimal | None:
    row = db.session.get(DeferredTierRate, tier)
    return row.annual_pct if row is not None else _DEFAULT_TIER_RATES.get(tier)


def resolve_annual_pct(customer_id: int) -> Decimal | None:
    """The effective annual % for a customer, most-specific first. None means
    "not allowed to defer" (a red-tier customer)."""
    from . import credit as credit_svc

    exc = db.session.execute(
        select(DeferredCustomerException).where(
            DeferredCustomerException.customer_id == customer_id
        )
    ).scalar_one_or_none()

    tier = credit_svc.get_tier(customer_id).tier
    if tier == "red":
        # Red can never defer — even an exception does not override the credit
        # rule that hard-blocks a red customer at checkout.
        return None
    if exc is not None:
        return to_money(exc.annual_pct)
    rate = _tier_rate(tier)
    if rate is not None:
        return to_money(rate)
    return to_money(get_settings().annual_pct_general)


def compute_fee(amount: Decimal, annual_pct: Decimal, days: int) -> Decimal:
    """fee = amount × annual_pct/100 / 365 × days, rounded to 2 dp."""
    raw = to_money(amount) * (to_money(annual_pct) / Decimal("100")) / Decimal("365") * Decimal(days)
    return raw.quantize(_FEE_SCALE, rounding=ROUND_HALF_UP)


def validate_days(days: int) -> int:
    s = get_settings()
    if days <= 0:
        raise BadRequest("مدة الأجل يجب أن تكون أكبر من صفر", code="deferred_days_invalid")
    if days > s.max_days:
        raise BadRequest(f"مدة الأجل تتجاوز الحد الأقصى ({s.max_days} يوم)", code="deferred_days_too_long")
    if s.allowed_days and days not in s.allowed_days:
        raise BadRequest("مدة الأجل غير متاحة — اختر من المدد المسموح بها", code="deferred_days_not_allowed")
    return days


def quote(*, amount: Decimal, days: int, customer_id: int, placed_on: date | None = None) -> dict[str, Any]:
    """Server-computed deferred quote. Raises/returns not-allowed for red."""
    annual = resolve_annual_pct(customer_id)
    if annual is None:
        return {"allowed": False, "reason": "التصنيف الأحمر لا يسمح بالبيع الآجل — نقدي فقط"}
    days = validate_days(days)
    amount = to_money(amount)
    fee = compute_fee(amount, annual, days)
    base = placed_on or date.today()
    # Customer-facing display values at 2 dp (the fee is already 2 dp).
    return {
        "allowed": True,
        "annual_pct": str(annual.quantize(_FEE_SCALE, rounding=ROUND_HALF_UP)),
        "days": days,
        "amount": str(amount.quantize(_FEE_SCALE, rounding=ROUND_HALF_UP)),
        "fee": str(fee),
        "total": str((amount + fee).quantize(_FEE_SCALE, rounding=ROUND_HALF_UP)),
        "due_date": (base + timedelta(days=days)).isoformat(),
    }


# ---------------------------------------------------------------- settings mutations


def serialize_settings() -> dict[str, Any]:
    s = get_settings()
    tiers = {t: _tier_rate(t) for t in _TIERS}
    excs = db.session.execute(
        select(DeferredCustomerException).order_by(DeferredCustomerException.id.desc())
    ).scalars().all()
    return {
        "annual_pct_general": str(to_money(s.annual_pct_general)),
        "default_days": s.default_days,
        "max_days": s.max_days,
        "allowed_days": list(s.allowed_days),
        "reviewed": s.reviewed,
        "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
        "tier_rates": {t: (str(to_money(v)) if v is not None else None) for t, v in tiers.items()},
        "exceptions": [
            {
                "customer_id": e.customer_id,
                "annual_pct": str(to_money(e.annual_pct)),
                "reason": e.reason,
            }
            for e in excs
        ],
    }


def update_settings(
    *,
    annual_pct_general: Decimal | None = None,
    default_days: int | None = None,
    max_days: int | None = None,
    allowed_days: list[int] | None = None,
) -> DeferredSetting:
    s = get_settings()
    if annual_pct_general is not None:
        if annual_pct_general < 0:
            raise BadRequest("النسبة لا يمكن أن تكون سالبة", code="pct_negative")
        s.annual_pct_general = to_money(annual_pct_general)
    if max_days is not None:
        if max_days <= 0:
            raise BadRequest("الحد الأقصى للمدة يجب أن يكون موجبًا", code="max_days_invalid")
        s.max_days = max_days
    if allowed_days is not None:
        cleaned = sorted({int(d) for d in allowed_days if int(d) > 0})
        if not cleaned:
            raise BadRequest("حدد مدة واحدة على الأقل", code="allowed_days_empty")
        if any(d > s.max_days for d in cleaned):
            raise BadRequest("إحدى المدد تتجاوز الحد الأقصى", code="allowed_days_exceed_max")
        s.allowed_days = cleaned
    if default_days is not None:
        s.default_days = default_days
    if s.default_days > s.max_days or (s.allowed_days and s.default_days not in s.allowed_days):
        raise BadRequest("المدة الافتراضية يجب أن تكون ضمن المدد المسموح بها", code="default_days_invalid")
    db.session.flush()
    return s


def set_tier_rate(*, tier: str, annual_pct: Decimal | None) -> DeferredTierRate:
    if tier not in _TIERS:
        raise BadRequest("تصنيف غير صالح", code="bad_tier")
    if annual_pct is not None and annual_pct < 0:
        raise BadRequest("النسبة لا يمكن أن تكون سالبة", code="pct_negative")
    row = db.session.get(DeferredTierRate, tier)
    if row is None:
        row = DeferredTierRate(tier=tier, annual_pct=to_money(annual_pct) if annual_pct is not None else None)
        db.session.add(row)
    else:
        row.annual_pct = to_money(annual_pct) if annual_pct is not None else None
    db.session.flush()
    return row


def set_exception(*, customer_id: int, annual_pct: Decimal, reason: str, set_by: int | None) -> DeferredCustomerException:
    if annual_pct < 0:
        raise BadRequest("النسبة لا يمكن أن تكون سالبة", code="pct_negative")
    if len(reason.strip()) < 5:
        raise BadRequest("السبب إلزامي (٥ أحرف فأكثر)", code="reason_required")
    row = db.session.execute(
        select(DeferredCustomerException).where(DeferredCustomerException.customer_id == customer_id)
    ).scalar_one_or_none()
    if row is None:
        row = DeferredCustomerException(
            customer_id=customer_id, annual_pct=to_money(annual_pct), reason=reason.strip(), set_by=set_by
        )
        db.session.add(row)
    else:
        row.annual_pct = to_money(annual_pct)
        row.reason = reason.strip()
        row.set_by = set_by
    db.session.flush()
    return row


def delete_exception(*, customer_id: int) -> None:
    row = db.session.execute(
        select(DeferredCustomerException).where(DeferredCustomerException.customer_id == customer_id)
    ).scalar_one_or_none()
    if row is None:
        raise NotFound("لا يوجد استثناء لهذا العميل", code="exception_not_found")
    db.session.delete(row)
    db.session.flush()


def mark_reviewed(*, reviewed_by: int | None) -> DeferredSetting:
    s = get_settings()
    s.reviewed = True
    s.reviewed_by = reviewed_by
    s.reviewed_at = datetime.now(UTC)
    db.session.flush()
    return s

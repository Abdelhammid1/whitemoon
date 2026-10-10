"""T-28 — flexible deferred-pricing engine: configurable annual rate × chosen
duration, per-order snapshot, settings gated by deferred.settings.manage, and
the customer quote endpoint (red not allowed)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.identity.models import CustomerProfile, User
from app.sales.models import DeferredSetting
from app.sales.services import deferred_pricing as dp
from tests.helpers import auth_header, create_user


def _uniq(p: str) -> str:
    return f"{p}{uuid.uuid4().hex[:6]}@wm.eg"


def _customer() -> User:
    u = create_user(kind="customer", email=_uniq("cust"), roles=("customer",))
    db.session.add(CustomerProfile(user_id=u.id, display_name="عميل"))
    db.session.commit()
    return u


def test_fee_formula() -> None:
    # 10,000 × 36% / 365 × 15 = 147.95 (2 dp, HALF_UP)
    assert dp.compute_fee(Decimal("10000"), Decimal("36"), 15) == Decimal("147.95")
    # Zero-rate → zero fee.
    assert dp.compute_fee(Decimal("10000"), Decimal("0"), 15) == Decimal("0.00")


def test_resolve_precedence_exception_over_tier_over_general(client) -> None:
    cust = _customer()
    # Brand-new customer → white tier → default white rate 36.
    assert dp.resolve_annual_pct(cust.id) == Decimal("36.00")
    # Tier override wins over general.
    dp.set_tier_rate(tier="white", annual_pct=Decimal("24"))
    db.session.commit()
    assert dp.resolve_annual_pct(cust.id) == Decimal("24.00")
    # A per-customer exception wins over the tier rate.
    dp.set_exception(customer_id=cust.id, annual_pct=Decimal("12"), reason="عميل مميز جدًا", set_by=None)
    db.session.commit()
    assert dp.resolve_annual_pct(cust.id) == Decimal("12.00")


def test_quote_endpoint_rejects_bad_days(client) -> None:
    cust = _customer()
    h = auth_header(client, email=cust.email)
    # 999 days is beyond max_days → 400.
    r = client.get("/credit/deferred-quote?amount=1000&days=999", headers=h)
    assert r.status_code == 400


def test_quote_endpoint_happy_path(client) -> None:
    cust = _customer()
    h = auth_header(client, email=cust.email)
    r = client.get("/credit/deferred-quote?amount=1000&days=15", headers=h)
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body["allowed"] is True
    assert body["annual_pct"] == "36.00"
    assert body["fee"] == "14.79"
    assert body["total"] == "1014.79"


def test_settings_requires_permission(client) -> None:
    # A plain staff user lacks deferred.settings.manage.
    staff = create_user(kind="staff", email=_uniq("staff"), roles=("staff",))
    h = auth_header(client, email=staff.email)
    assert client.get("/credit/deferred-settings", headers=h).status_code == 403

    # An admin has it.
    admin = create_user(kind="admin", email=_uniq("adm"), roles=("admin",))
    ha = auth_header(client, email=admin.email)
    r = client.get("/credit/deferred-settings", headers=ha)
    assert r.status_code == 200
    assert r.get_json()["reviewed"] is False


def test_delegated_staff_can_manage_settings(client) -> None:
    """Step 0 delegation: a staff user granted deferred.settings.manage directly
    (without the admin role) can reach the settings."""
    staff = create_user(kind="staff", email=_uniq("staff"), roles=("staff",))
    admin = create_user(kind="admin", email=_uniq("adm"), roles=("admin.high",))
    ha = auth_header(client, email=admin.email)
    g = client.post(f"/admin/users/{staff.id}/permissions", json={"code": "deferred.settings.manage"}, headers=ha)
    assert g.status_code == 200, g.get_json()

    h = auth_header(client, email=staff.email)
    assert client.get("/credit/deferred-settings", headers=h).status_code == 200


def test_review_marks_reviewed(client) -> None:
    admin = create_user(kind="admin", email=_uniq("adm"), roles=("admin",))
    h = auth_header(client, email=admin.email)
    r = client.post("/credit/deferred-settings/review", headers=h)
    assert r.status_code == 200 and r.get_json()["reviewed"] is True
    row = db.session.get(DeferredSetting, 1)
    assert row is not None and row.reviewed is True


def test_snapshot_unaffected_by_later_rate_change(client) -> None:
    """A placed order's DeferredTerm snapshot keeps its rate even after the
    settings change — the core T-28 guarantee."""
    from app.accounting.services import deferred as deferred_svc

    term = deferred_svc.create(
        order_id=999001,
        cash_price=Decimal("1000"),
        deferred_price=Decimal("1014.79"),
        early_settlement_discount=Decimal("7.395"),
        early_settlement_before=None,
    )
    term.annual_pct = Decimal("36.00")
    term.days = 15
    term.fee = Decimal("14.79")
    db.session.commit()

    dp.set_tier_rate(tier="white", annual_pct=Decimal("12"))
    db.session.commit()

    from app.accounting.models import DeferredTerm

    stored = db.session.execute(
        select(DeferredTerm).where(DeferredTerm.order_id == 999001)
    ).scalar_one()
    assert stored.annual_pct == Decimal("36.00")  # snapshot unchanged

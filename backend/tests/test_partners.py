"""EPIC 6 — channel partners (agents & branches): deposits, terms, accruals."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.accounting.models import Account, JournalLine
from app.commerce.models import Order
from app.common.errors import BadRequest, Conflict
from app.extensions import db
from app.identity.models import ChannelPartnerProfile
from app.partners.services import partners as svc
from tests.helpers import create_user


def _make_partner(email: str, ptype: str = "agent"):
    u = create_user(kind=ptype, email=email, roles=(ptype,))
    db.session.add(
        ChannelPartnerProfile(user_id=u.id, type=ptype, display_name="شريك", geo_scope="القاهرة")
    )
    db.session.commit()
    return u


def _realized_order(partner_id: int, customer_id: int, *, amount: str, year: int, month: int, status: str = "fulfilled", seq: int = 1):
    o = Order(
        number=f"T-{partner_id}-{year}{month:02d}-{seq}",
        customer_id=customer_id,
        status=status,
        payment_mode="cash",
        total_cash=Decimal(amount),
        total_deferred=Decimal(amount),
        partner_user_id=partner_id,
        placed_at=datetime(year, month, 15, tzinfo=UTC),
    )
    db.session.add(o)
    db.session.commit()
    return o


# ---------------------------------------------------------------- terms


def test_set_terms_for_agent(client) -> None:
    agent = _make_partner("agent1@example.com")
    t = svc.set_terms(
        partner_id=agent.id,
        earns_commission=True,
        commission_rate_pct=Decimal("5"),
        earns_investment_return=True,
        investment_return_rate_pct=Decimal("2"),
        actor_user_id=1,
    )
    assert t.earns_commission and t.commission_rate_pct == Decimal("5.00")
    assert t.earns_investment_return and t.investment_return_rate_pct == Decimal("2.00")


def test_branch_cannot_earn(client) -> None:
    branch = _make_partner("branch1@example.com", ptype="branch")
    with pytest.raises(BadRequest):
        svc.set_terms(
            partner_id=branch.id,
            earns_commission=True,
            commission_rate_pct=Decimal("5"),
            earns_investment_return=False,
            investment_return_rate_pct=Decimal("0"),
            actor_user_id=1,
        )


# ---------------------------------------------------------------- deposits (US-6.1)


def test_deposit_posts_liability_and_audits(client) -> None:
    agent = _make_partner("dep@example.com")
    dep = svc.record_deposit(
        partner_id=agent.id,
        amount=Decimal("50000"),
        deposit_date=date(2026, 1, 10),
        recovery_conditions="يُسترد عند إنهاء التعاقد بعد تسوية الذمم",
        posted_by=1,
    )
    assert dep.status == "held"
    assert dep.journal_entry_id is not None
    # A credit line hits 2120 (Agent Deposits), i.e. a company liability.
    acc_2120 = db.session.execute(
        db.select(Account).where(Account.code == "2120")
    ).scalar_one()
    line = db.session.execute(
        db.select(JournalLine).where(
            JournalLine.entry_id == dep.journal_entry_id,
            JournalLine.account_id == acc_2120.id,
        )
    ).scalar_one()
    assert line.credit == Decimal("50000.0000")
    # Audit row persisted (atomic with the deposit).
    from app.audit.models import AuditEvent
    ev = db.session.execute(
        db.select(AuditEvent).where(AuditEvent.action == "partner.deposit.received")
    ).first()
    assert ev is not None


def test_deposit_refund_reverses(client) -> None:
    agent = _make_partner("dep2@example.com")
    dep = svc.record_deposit(
        partner_id=agent.id,
        amount=Decimal("10000"),
        deposit_date=date(2026, 1, 10),
        recovery_conditions="يُسترد عند إنهاء التعاقد",
        posted_by=1,
    )
    refunded = svc.refund_deposit(deposit_id=dep.id, reason="إنهاء التعاقد وتسوية", posted_by=1)
    assert refunded.status == "refunded"
    assert refunded.refund_journal_entry_id is not None
    with pytest.raises(Conflict):
        svc.refund_deposit(deposit_id=dep.id, reason="محاولة مكررة", posted_by=1)


# ---------------------------------------------------------------- accruals (US-6.2)


def test_commission_accrual_from_realized_sales(client) -> None:
    agent = _make_partner("acc@example.com")
    cust = create_user(kind="customer", email="c1@example.com", roles=("customer",))
    db.session.commit()
    svc.set_terms(
        partner_id=agent.id,
        earns_commission=True,
        commission_rate_pct=Decimal("10"),
        earns_investment_return=False,
        investment_return_rate_pct=Decimal("0"),
        actor_user_id=1,
    )
    _realized_order(agent.id, cust.id, amount="100000", year=2026, month=3, seq=1)
    _realized_order(agent.id, cust.id, amount="50000", year=2026, month=3, seq=2)
    # A pending order in the same month must NOT count.
    _realized_order(agent.id, cust.id, amount="999999", year=2026, month=3, status="pending", seq=3)
    acc = svc.compute_accrual(partner_id=agent.id, kind="commission", year=2026, month=3, posted_by=1)
    assert acc.basis_amount == Decimal("150000.0000")
    assert acc.amount == Decimal("15000.0000")  # 10% of 150k
    assert acc.journal_entry_id is not None


def test_accrual_not_entitled_raises(client) -> None:
    agent = _make_partner("acc2@example.com")
    svc.set_terms(
        partner_id=agent.id,
        earns_commission=False,
        commission_rate_pct=Decimal("0"),
        earns_investment_return=False,
        investment_return_rate_pct=Decimal("0"),
        actor_user_id=1,
    )
    with pytest.raises(BadRequest):
        svc.compute_accrual(partner_id=agent.id, kind="commission", year=2026, month=3, posted_by=1)


def test_accrual_is_idempotent_per_period(client) -> None:
    agent = _make_partner("acc3@example.com")
    cust = create_user(kind="customer", email="c3@example.com", roles=("customer",))
    db.session.commit()
    svc.set_terms(
        partner_id=agent.id,
        earns_commission=True,
        commission_rate_pct=Decimal("5"),
        earns_investment_return=False,
        investment_return_rate_pct=Decimal("0"),
        actor_user_id=1,
    )
    _realized_order(agent.id, cust.id, amount="20000", year=2026, month=4, seq=1)
    svc.compute_accrual(partner_id=agent.id, kind="commission", year=2026, month=4, posted_by=1)
    with pytest.raises(Conflict):
        svc.compute_accrual(partner_id=agent.id, kind="commission", year=2026, month=4, posted_by=1)


def test_investment_return_accrual(client) -> None:
    agent = _make_partner("acc4@example.com")
    cust = create_user(kind="customer", email="c4@example.com", roles=("customer",))
    db.session.commit()
    svc.set_terms(
        partner_id=agent.id,
        earns_commission=False,
        commission_rate_pct=Decimal("0"),
        earns_investment_return=True,
        investment_return_rate_pct=Decimal("3"),
        actor_user_id=1,
    )
    _realized_order(agent.id, cust.id, amount="200000", year=2026, month=5, seq=1)
    acc = svc.compute_accrual(partner_id=agent.id, kind="investment_return", year=2026, month=5, posted_by=1)
    assert acc.amount == Decimal("6000.0000")  # 3% of 200k

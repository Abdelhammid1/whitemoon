"""The five reports produce balanced totals on a seeded fixture."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.accounting.services import reports as reports_svc
from app.accounting.services.events import post
from app.accounting.services.reports import ReportFilter
from app.extensions import db


def _seed_a_tiny_month() -> None:
    """Two cash sales + one supply receipt — enough to exercise the reports."""
    post(
        event_type="order.placed.cash",
        entry_date=date(2026, 10, 1),
        description="sale 1",
        context={"amount": Decimal("1000"), "category": "food"},
    )
    post(
        event_type="order.placed.cash",
        entry_date=date(2026, 10, 2),
        description="sale 2",
        context={"amount": Decimal("500"), "category": "clothing"},
    )
    post(
        event_type="supply.received",
        entry_date=date(2026, 10, 1),
        description="restock food",
        context={"cost": Decimal("600"), "category": "food"},
    )
    db.session.commit()


def _f(year: int = 2026, month: int = 10) -> ReportFilter:
    return ReportFilter(
        date_from=date(year, month, 1), date_to=date(year, month, 28)
    )


def test_trial_balance_is_balanced(client) -> None:
    _seed_a_tiny_month()
    tb = reports_svc.trial_balance(_f())
    assert tb["totals"]["balanced"] is True
    assert tb["rows"], "trial balance should have rows after seeding"


def test_income_statement_sees_revenue_and_cogs(client) -> None:
    _seed_a_tiny_month()
    pl = reports_svc.income_statement(_f())
    rev_codes = {r["code"] for r in pl["revenues"]}
    assert {"4110", "4120"} <= rev_codes
    assert Decimal(pl["totals"]["revenue"]) == Decimal("1500.0000")


def test_balance_sheet_balances(client) -> None:
    _seed_a_tiny_month()
    bs = reports_svc.balance_sheet(_f())
    # Totals must satisfy A = L + E for the subset we've generated.
    assets = Decimal(bs["totals"]["assets"])
    liab = Decimal(bs["totals"]["liabilities"])
    eq = Decimal(bs["totals"]["equity"])
    assert assets - (liab + eq) == Decimal("0")


def test_general_ledger_runs(client) -> None:
    _seed_a_tiny_month()
    gl = reports_svc.general_ledger(
        account_code="4110",
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 31),
    )
    assert gl["account"]["code"] == "4110"
    assert gl["rows"]


def test_cash_flow_runs(client) -> None:
    _seed_a_tiny_month()
    cf = reports_svc.cash_flow(_f())
    assert "sources" in cf
    assert "uses" in cf

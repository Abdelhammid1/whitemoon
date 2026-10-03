"""CoA seed matches docs/02 — the key accounts introduced in reviewer round 2."""

from __future__ import annotations

from sqlalchemy import select

from app.accounting.models import Account, EventJournalMap
from app.extensions import db


def test_critical_accounts_present() -> None:
    codes = {c for c in db.session.execute(select(Account.code)).scalars().all()}
    # Reviewer round 2: 5281 added, 5290 added, 2121 removed.
    assert "5281" in codes
    assert "5290" in codes
    assert "2121" not in codes
    # Core accounts the journal map references.
    for code in ("1111", "1112", "1120", "1131", "1132", "1140", "1151", "1152",
                 "1153", "1154", "2111", "2112", "2120", "2130", "2140",
                 "4110", "4120", "4200", "4300", "5110", "5120", "5281", "5290",
                 "9100"):
        assert code in codes, f"missing account {code}"


def test_event_map_covers_core_events() -> None:
    types = {
        r for r in db.session.execute(select(EventJournalMap.event_type)).scalars()
    }
    for event in (
        "order.placed.cash",
        "order.placed.deferred",
        "inventory.issued",
        "payment.ocr.matched.upload",
        "payment.ocr.matched.confirm",
        "payment.early_discount.applied",
        "supply.received",
        "agent.commission.accrued",
        "agent.investment_return.accrued",
    ):
        assert event in types, f"event {event} missing from map"


def test_agent_commission_posts_to_5281_not_5280() -> None:
    rows = db.session.execute(
        select(EventJournalMap)
        .where(EventJournalMap.event_type == "agent.commission.accrued")
        .order_by(EventJournalMap.step)
    ).scalars().all()
    assert len(rows) == 2
    debit_row = next(r for r in rows if r.side == "debit")
    assert debit_row.account_code == "5281"


def test_investment_return_posts_to_5290() -> None:
    rows = db.session.execute(
        select(EventJournalMap)
        .where(EventJournalMap.event_type == "agent.investment_return.accrued")
        .order_by(EventJournalMap.step)
    ).scalars().all()
    debit_row = next(r for r in rows if r.side == "debit")
    assert debit_row.account_code == "5290"


def test_inventory_issued_credit_side_is_location_aware() -> None:
    rows = db.session.execute(
        select(EventJournalMap)
        .where(EventJournalMap.event_type == "inventory.issued")
        .order_by(EventJournalMap.step)
    ).scalars().all()
    credit_row = next(r for r in rows if r.side == "credit")
    rule = credit_row.rule_json
    assert rule is not None
    assert "by_location" in rule
    locations = rule["by_location"]
    assert locations["supplier"] == "1151_or_1152"
    assert locations["channel_partner"] == "1153"
    assert locations["in_transit"] == "1154"

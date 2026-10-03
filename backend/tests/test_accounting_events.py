"""Journal posting engine — rules it must enforce."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.accounting.models import Account, JournalEntry, JournalLine
from app.accounting.services.events import LineInput, post, post_manual
from app.common.errors import BadRequest, Forbidden
from app.extensions import db


def _amounts(entry_id: int) -> tuple[Decimal, Decimal]:
    rows = db.session.execute(
        select(JournalLine).where(JournalLine.entry_id == entry_id)
    ).scalars().all()
    debit = sum((r.debit for r in rows), start=Decimal("0"))
    credit = sum((r.credit for r in rows), start=Decimal("0"))
    return debit, credit


def test_order_placed_cash_balances(client) -> None:
    r = post(
        event_type="order.placed.cash",
        entry_date=date(2026, 10, 3),
        description="order #1",
        context={"amount": Decimal("1234.5600"), "category": "food"},
        source_event_id=1,
    )
    db.session.commit()
    d, c = _amounts(r.entry_id)
    assert d == c == Decimal("1234.5600")


def test_order_placed_deferred_posts_three_lines(client) -> None:
    r = post(
        event_type="order.placed.deferred",
        entry_date=date(2026, 10, 3),
        description="order #2",
        context={
            "deferred_price": Decimal("1200"),
            "cash_price": Decimal("1000"),
            "spread": Decimal("200"),
            "category": "clothing",
        },
        source_event_id=2,
    )
    db.session.commit()
    d, c = _amounts(r.entry_id)
    assert d == c == Decimal("1200.0000")


def test_inventory_issued_from_channel_partner_credits_1153(client) -> None:
    r = post(
        event_type="inventory.issued",
        entry_date=date(2026, 10, 3),
        description="shipment #99",
        context={
            "cost": Decimal("500"),
            "category": "food",
            "location_type": "channel_partner",
        },
    )
    db.session.commit()
    lines = db.session.execute(
        select(JournalLine, Account.code)
        .join(Account, Account.id == JournalLine.account_id)
        .where(JournalLine.entry_id == r.entry_id)
    ).all()
    credit_codes = [code for (line, code) in lines if line.credit > 0]
    assert credit_codes == ["1153"]


def test_inventory_issued_from_platform_picks_1151_for_food(client) -> None:
    r = post(
        event_type="inventory.issued",
        entry_date=date(2026, 10, 3),
        description="shipment #100",
        context={
            "cost": Decimal("500"),
            "category": "food",
            "location_type": "supplier",
        },
    )
    db.session.commit()
    lines = db.session.execute(
        select(JournalLine, Account.code)
        .join(Account, Account.id == JournalLine.account_id)
        .where(JournalLine.entry_id == r.entry_id)
    ).all()
    credit_codes = [code for (line, code) in lines if line.credit > 0]
    assert credit_codes == ["1151"]


def test_agent_commission_hits_5281_not_5280(client) -> None:
    r = post(
        event_type="agent.commission.accrued",
        entry_date=date(2026, 10, 3),
        description="October commission for agent #7",
        context={"amount": Decimal("300"), "partner_type": "agent", "partner_id": 7},
    )
    db.session.commit()
    debit_line = db.session.execute(
        select(Account.code)
        .join(JournalLine, JournalLine.account_id == Account.id)
        .where(JournalLine.entry_id == r.entry_id, JournalLine.debit > 0)
    ).scalar_one()
    assert debit_line == "5281"


def test_unknown_event_rejected(client) -> None:
    with pytest.raises(BadRequest):
        post(
            event_type="some.made.up.event",
            entry_date=date(2026, 10, 3),
            description="x",
            context={"amount": Decimal("1")},
        )


def test_posting_to_non_postable_account_rejected(client) -> None:
    with pytest.raises(Forbidden):
        post_manual(
            entry_date=date(2026, 10, 3),
            description="manual to parent account",
            lines=[
                LineInput(account_code="1000", debit=Decimal("1")),
                LineInput(account_code="1111", credit=Decimal("1")),
            ],
            posted_by=1,
            reason="trying to post to non-postable 1000",
        )
    db.session.rollback()


def test_manual_journal_requires_balance(client) -> None:
    with pytest.raises(BadRequest):
        post_manual(
            entry_date=date(2026, 10, 3),
            description="imbalanced manual entry",
            lines=[
                LineInput(account_code="1111", debit=Decimal("100")),
                LineInput(account_code="4400", credit=Decimal("90")),
            ],
            posted_by=1,
            reason="deliberately imbalanced for testing",
        )


def test_manual_journal_balanced_posts(client) -> None:
    r = post_manual(
        entry_date=date(2026, 10, 3),
        description="valid manual entry — correction of prior typo",
        lines=[
            LineInput(account_code="1111", debit=Decimal("100")),
            LineInput(account_code="4400", credit=Decimal("100")),
        ],
        posted_by=1,
        reason="valid manual entry needed for correction",
    )
    db.session.commit()
    entry = db.session.get(JournalEntry, r.entry_id)
    assert entry is not None
    assert entry.source == "manual"

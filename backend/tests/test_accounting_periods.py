"""Period open / close / reopen + guard on posting into a closed period."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import DBAPIError

from app.accounting.services import periods as periods_svc
from app.accounting.services.events import LineInput, post, post_manual
from app.extensions import db


def test_closing_a_period_blocks_subsequent_posts(client) -> None:
    periods_svc.ensure_period(year=2026, month=10)
    db.session.commit()

    # Baseline — posting into October works.
    post(
        event_type="order.placed.cash",
        entry_date=date(2026, 10, 15),
        description="pre-close order",
        context={"amount": Decimal("100"), "category": "food"},
    )
    db.session.commit()

    periods_svc.close(year=2026, month=10, closed_by=1)
    db.session.commit()

    # Now posting into October must fail at the trigger.
    with pytest.raises(DBAPIError):
        post(
            event_type="order.placed.cash",
            entry_date=date(2026, 10, 20),
            description="post-close order",
            context={"amount": Decimal("50"), "category": "food"},
        )
        db.session.commit()
    db.session.rollback()


def test_closed_period_override_allows_manual_post(client) -> None:
    periods_svc.ensure_period(year=2026, month=10)
    periods_svc.close(year=2026, month=10, closed_by=1)
    db.session.commit()

    r = post_manual(
        entry_date=date(2026, 10, 25),
        description="late correction, approved by finance",
        lines=[
            LineInput(account_code="1111", debit=Decimal("10")),
            LineInput(account_code="4400", credit=Decimal("10")),
        ],
        posted_by=1,
        reason="correcting a bank-fee misclassification",
        allow_closed_period=True,
    )
    db.session.commit()
    assert r.entry_id > 0


def test_reopen_toggles_state(client) -> None:
    periods_svc.ensure_period(year=2026, month=10)
    periods_svc.close(year=2026, month=10, closed_by=1)
    period = periods_svc.reopen(year=2026, month=10, reopened_by=1)
    assert period.is_closed is False
    assert period.closed_at is None

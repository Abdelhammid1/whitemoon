"""Shariah-compliant deferred terms (US-3.4)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.accounting.services import deferred as deferred_svc
from app.common.errors import BadRequest, Conflict
from app.extensions import db


def test_create_locks_cash_and_deferred_prices(client) -> None:
    term = deferred_svc.create(
        order_id=1,
        cash_price=Decimal("1000"),
        deferred_price=Decimal("1200"),
        early_settlement_discount=Decimal("100"),
        early_settlement_before=date(2026, 11, 1),
    )
    db.session.commit()
    assert term.cash_price == Decimal("1000.0000")
    assert term.deferred_price == Decimal("1200.0000")
    assert term.discount_applied is False


def test_deferred_price_must_be_gte_cash(client) -> None:
    with pytest.raises(BadRequest):
        deferred_svc.create(
            order_id=2,
            cash_price=Decimal("1200"),
            deferred_price=Decimal("1000"),
            early_settlement_discount=Decimal("0"),
            early_settlement_before=None,
        )


def test_duplicate_order_rejected(client) -> None:
    deferred_svc.create(
        order_id=3,
        cash_price=Decimal("500"),
        deferred_price=Decimal("600"),
        early_settlement_discount=Decimal("0"),
        early_settlement_before=None,
    )
    db.session.commit()
    with pytest.raises(Conflict):
        deferred_svc.create(
            order_id=3,
            cash_price=Decimal("500"),
            deferred_price=Decimal("600"),
            early_settlement_discount=Decimal("0"),
            early_settlement_before=None,
        )


def test_apply_early_discount_within_window(client) -> None:
    deferred_svc.create(
        order_id=4,
        cash_price=Decimal("1000"),
        deferred_price=Decimal("1100"),
        early_settlement_discount=Decimal("50"),
        early_settlement_before=date(2026, 11, 1),
    )
    db.session.commit()

    term = deferred_svc.apply_early_discount(order_id=4, settled_on=date(2026, 10, 20))
    db.session.commit()
    assert term.discount_applied is True


def test_apply_early_discount_past_deadline_rejected(client) -> None:
    deferred_svc.create(
        order_id=5,
        cash_price=Decimal("1000"),
        deferred_price=Decimal("1100"),
        early_settlement_discount=Decimal("50"),
        early_settlement_before=date(2026, 11, 1),
    )
    db.session.commit()
    with pytest.raises(BadRequest):
        deferred_svc.apply_early_discount(
            order_id=5, settled_on=date(2026, 11, 15)
        )

"""Shariah-compliant deferred terms (US-3.4).

- `create` locks `cash_price` + `deferred_price` + `early_settlement_discount`
  at order time; no daily accrual, no late-payment surcharge.
- `apply_early_discount` is idempotent — once the discount is applied,
  calling again does nothing.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select

from ...common.errors import BadRequest, Conflict, NotFound
from ...common.money import to_money
from ...extensions import db
from ..models import DeferredTerm


def create(
    *,
    order_id: int,
    cash_price: Decimal,
    deferred_price: Decimal,
    early_settlement_discount: Decimal,
    early_settlement_before: date | None,
) -> DeferredTerm:
    cash = to_money(cash_price)
    deferred = to_money(deferred_price)
    discount = to_money(early_settlement_discount)
    if deferred < cash:
        raise BadRequest(
            "deferred_price must be ≥ cash_price",
            code="deferred_lt_cash",
        )
    if discount < 0:
        raise BadRequest("discount must be ≥ 0", code="discount_negative")

    existing = db.session.execute(
        select(DeferredTerm).where(DeferredTerm.order_id == order_id)
    ).scalar_one_or_none()
    if existing is not None:
        raise Conflict(
            "deferred terms already set for this order",
            code="deferred_already_set",
        )

    term = DeferredTerm(
        order_id=order_id,
        cash_price=cash,
        deferred_price=deferred,
        early_settlement_discount=discount,
        early_settlement_before=early_settlement_before,
    )
    db.session.add(term)
    db.session.flush()
    return term


def apply_early_discount(*, order_id: int, settled_on: date) -> DeferredTerm:
    term = db.session.execute(
        select(DeferredTerm).where(DeferredTerm.order_id == order_id)
    ).scalar_one_or_none()
    if term is None:
        raise NotFound("deferred terms not found", code="deferred_not_found")
    if term.discount_applied:
        return term  # idempotent

    if (
        term.early_settlement_before is None
        or settled_on > term.early_settlement_before
    ):
        raise BadRequest(
            "settlement is not early (past the discount deadline)",
            code="not_early",
        )

    term.discount_applied = True
    term.settled_at = datetime.now(UTC)
    db.session.flush()
    return term

"""EPIC 11 — compliance: ETA readiness (US-11.1) + EGP-only (US-11.2)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.commerce.models import Order
from app.common.errors import BadRequest
from app.compliance.services import compliance as svc
from app.extensions import db
from app.inventory.services import products as products_svc
from tests.helpers import create_user


def _product():
    return products_svc.create_product(
        sku=f"P-{uuid.uuid4().hex[:8]}", name_ar="صنف", category="food", created_by=1
    )


def test_set_eta_and_readiness_report(client) -> None:
    p = _product()
    updated = svc.set_eta(product_id=p.id, eta_code="EG-1234567", eta_ready=True, actor_user_id=1)
    assert updated.eta_code == "EG-1234567"
    assert updated.eta_ready is True

    report = svc.readiness_report()
    assert report["currency"] == "EGP"
    assert report["eta_ready"] >= 1


def test_cannot_be_eta_ready_without_code(client) -> None:
    p = _product()
    with pytest.raises(BadRequest):
        svc.set_eta(product_id=p.id, eta_code=None, eta_ready=True, actor_user_id=1)


def test_assert_egp_rejects_foreign_currency(client) -> None:
    svc.assert_egp("EGP")  # ok
    with pytest.raises(BadRequest):
        svc.assert_egp("USD")


def test_db_check_rejects_non_egp_row(client) -> None:
    # US-11.2 is also guaranteed at the DB level: a monetary row in another
    # currency is refused by the CHECK constraint.
    cust = create_user(kind="customer", email=f"c{uuid.uuid4().hex[:6]}@example.com", roles=("customer",))
    db.session.commit()
    db.session.add(
        Order(
            number=f"ORD-{uuid.uuid4().hex[:8]}",
            customer_id=cust.id,
            status="pending",
            payment_mode="cash",
            total_cash=Decimal("100"),
            total_deferred=Decimal("100"),
            currency="USD",
        )
    )
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()

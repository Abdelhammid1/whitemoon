"""EPIC 8 — Point of Sale: shared inventory + batched settlement."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.accounting.models import Account, JournalEntry, JournalLine
from app.common.errors import BadRequest
from app.extensions import db
from app.inventory.services import products as products_svc
from app.inventory.services import stock as stock_svc
from app.pos.services import pos as svc
from app.pos.services.pos import SaleLineInput
from tests.helpers import create_user


def _user(kind: str = "supplier"):
    u = create_user(kind=kind, email=f"{kind}{uuid.uuid4().hex[:6]}@example.com", roles=(kind,))
    db.session.commit()
    return u


def _product(sku: str, category: str = "food"):
    return products_svc.create_product(sku=sku, name_ar="صنف", category=category, created_by=1)


def _seed(owner_id: int, product_id: int, qty: str, loc_id: int):
    stock_svc.manual_adjust(
        supplier_id=owner_id,
        product_id=product_id,
        location_type="channel_partner",
        location_id=loc_id,
        delta=Decimal(qty),
    )


def test_sale_deducts_shared_stock_immediately_but_unposted(client) -> None:
    supplier = _user()
    cashier = _user(kind="branch")
    product = _product("POS-1", "food")
    _seed(supplier.id, product.id, "50", loc_id=cashier.id)

    sale = svc.create_sale(
        cashier_id=cashier.id,
        location_type="channel_partner",
        location_id=cashier.id,
        lines=[SaleLineInput(product_id=product.id, supplier_id=supplier.id, qty=Decimal("10"), unit_price=Decimal("25"))],
    )
    assert sale.total == Decimal("250.0000")
    assert sale.posted is False  # accounting deferred to batch (US-8.2)

    # Stock deducted immediately from the SAME inventory row (single source).
    bal = stock_svc.get_balance(
        supplier_id=supplier.id, product_id=product.id, location_type="channel_partner", location_id=cashier.id
    )
    assert bal is not None and bal.on_hand == Decimal("40.0000")


def test_sale_insufficient_stock_rejected(client) -> None:
    supplier = _user()
    cashier = _user(kind="branch")
    product = _product("POS-2", "food")
    _seed(supplier.id, product.id, "5", loc_id=cashier.id)
    with pytest.raises(BadRequest):
        svc.create_sale(
            cashier_id=cashier.id,
            location_type="channel_partner",
            location_id=cashier.id,
            lines=[SaleLineInput(product_id=product.id, supplier_id=supplier.id, qty=Decimal("10"), unit_price=Decimal("25"))],
        )


def test_batch_settlement_posts_pos_revenue_once(client) -> None:
    supplier = _user()
    cashier = _user(kind="branch")
    food = _product("POS-F", "food")
    cloth = _product("POS-C", "clothing")
    _seed(supplier.id, food.id, "100", loc_id=cashier.id)
    _seed(supplier.id, cloth.id, "100", loc_id=cashier.id)

    svc.create_sale(
        cashier_id=cashier.id, location_type="channel_partner", location_id=cashier.id,
        lines=[SaleLineInput(product_id=food.id, supplier_id=supplier.id, qty=Decimal("4"), unit_price=Decimal("50"))],
    )
    svc.create_sale(
        cashier_id=cashier.id, location_type="channel_partner", location_id=cashier.id,
        lines=[SaleLineInput(product_id=cloth.id, supplier_id=supplier.id, qty=Decimal("2"), unit_price=Decimal("100"))],
    )

    batch = svc.settle_batch(posted_by=1)
    assert batch.sale_count == 2
    assert batch.total == Decimal("400.0000")  # 200 food + 200 clothing
    assert batch.journal_entry_id is not None

    # POS revenue accounts 4130 (food) / 4140 (clothing) both credited across
    # the batch's per-category entries.
    credited = set(
        db.session.execute(
            select(Account.code)
            .join(JournalLine, JournalLine.account_id == Account.id)
            .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
            .where(
                JournalEntry.source_event_type == "pos.sale.batch",
                JournalEntry.source_event_id == str(batch.id),
                JournalLine.credit > 0,
            )
        ).scalars()
    )
    assert {"4130", "4140"} <= credited

    # All sales now posted; a second settlement has nothing to post.
    assert all(s.posted for s in svc.list_sales())
    with pytest.raises(BadRequest):
        svc.settle_batch(posted_by=1)

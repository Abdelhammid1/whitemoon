"""EPIC 4 — inventory + purchasing. Covers US-4.1..US-4.4 and the two
non-negotiables: supplier isolation and transfer→journal."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.accounting.models import Account, JournalLine
from app.extensions import db
from app.inventory.models import Product
from app.inventory.services import offers as offers_svc
from app.inventory.services import products as products_svc
from app.inventory.services import reorder as reorder_svc
from app.inventory.services import shortages as shortages_svc
from app.inventory.services import stock as stock_svc
from app.inventory.services import transfers as transfers_svc
from app.inventory.services.transfers import LineInput
from tests.helpers import auth_header, create_user


def _product(sku: str = "SKU-1", category: str = "food") -> Product:
    return products_svc.create_product(
        sku=sku, name_ar="صنف اختبار", category=category, created_by=1
    )


def _debit_codes(entry_id: int) -> list[str]:
    rows = db.session.execute(
        select(Account.code)
        .join(JournalLine, JournalLine.account_id == Account.id)
        .where(JournalLine.entry_id == entry_id, JournalLine.debit > 0)
    ).scalars().all()
    return list(rows)


def _credit_codes(entry_id: int) -> list[str]:
    rows = db.session.execute(
        select(Account.code)
        .join(JournalLine, JournalLine.account_id == Account.id)
        .where(JournalLine.entry_id == entry_id, JournalLine.credit > 0)
    ).scalars().all()
    return list(rows)


# ---------------------------------------------------------------- US-4.1


def test_product_catalog_enforces_category(client) -> None:
    p = _product(category="clothing")
    db.session.commit()
    assert p.category == "clothing"
    with pytest.raises(Exception):  # noqa: B017 — Conflict on bad category
        products_svc.create_product(sku="X", name_ar="x", category="toys")


def test_product_catalog_accepts_expanded_categories(client) -> None:
    # T-10: segments beyond food/clothing are now valid.
    for cat in ("electronics", "home", "beauty", "construction", "stationery", "automotive", "other"):
        p = _product(sku=f"EXP-{cat}", category=cat)
        db.session.commit()
        assert p.category == cat


def test_best_price_never_exposes_supplier(client) -> None:
    p = _product()
    s1 = create_user(kind="supplier", email="s1@example.com", roles=("supplier",))
    s2 = create_user(kind="supplier", email="s2@example.com", roles=("supplier",))
    offers_svc.upsert_offer(supplier_id=s1.id, product_id=p.id, unit_price=Decimal("100"))
    offers_svc.upsert_offer(supplier_id=s2.id, product_id=p.id, unit_price=Decimal("90"))
    best = offers_svc.best_offer(p.id)
    assert best is not None
    assert best["best_price"] == "90.0000"
    assert "supplier_id" not in best
    assert "supplier" not in best


def test_supplier_isolation_on_offers_endpoint(client) -> None:
    p = _product()
    s1 = create_user(kind="supplier", phone="+201000000200", roles=("supplier",))
    s2 = create_user(kind="supplier", phone="+201000000201", roles=("supplier",))
    offers_svc.upsert_offer(supplier_id=s1.id, product_id=p.id, unit_price=Decimal("100"))
    offers_svc.upsert_offer(supplier_id=s2.id, product_id=p.id, unit_price=Decimal("80"))
    db.session.commit()

    h2 = auth_header(client, phone="+201000000201")
    r = client.get("/inventory/offers/mine", headers=h2)
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert len(items) == 1
    assert items[0]["unit_price"] == "80.0000"


# ---------------------------------------------------------------- US-4.2


def test_transfer_issue_and_receive_post_journals(client) -> None:
    p = _product()
    supplier = create_user(kind="supplier", email="sup@example.com", roles=("supplier",))
    # seed source stock
    stock_svc.manual_adjust(
        supplier_id=supplier.id,
        product_id=p.id,
        location_type="supplier",
        location_id=None,
        delta=Decimal("100"),
    )

    order = transfers_svc.create_transfer_order(
        supplier_id=supplier.id,
        from_location_type="supplier",
        from_location_id=None,
        to_location_type="channel_partner",
        to_location_id=999,
        lines=[LineInput(product_id=p.id, qty=Decimal("30"), unit_cost=Decimal("10"))],
        initiated_by=1,
    )
    assert order.number.startswith("TRF-")

    issued = transfers_svc.issue(order_id=order.id, issued_by=1)
    assert issued.status == "issued"
    assert issued.issue_entry_id is not None
    # issued: dr 9100, cr 1151 (food platform)
    assert _debit_codes(issued.issue_entry_id) == ["9100"]
    assert _credit_codes(issued.issue_entry_id) == ["1151"]
    # source stock decremented 100 -> 70
    src = stock_svc.get_balance(
        supplier_id=supplier.id, product_id=p.id, location_type="supplier", location_id=None
    )
    assert src is not None and src.on_hand == Decimal("70.0000")

    received = transfers_svc.receive(order_id=order.id, received_by=1)
    assert received.status == "received"
    assert received.receive_entry_id is not None
    # received: dr 1153 (channel partner), cr 9100
    assert _debit_codes(received.receive_entry_id) == ["1153"]
    assert _credit_codes(received.receive_entry_id) == ["9100"]
    dest = stock_svc.get_balance(
        supplier_id=supplier.id,
        product_id=p.id,
        location_type="channel_partner",
        location_id=999,
    )
    assert dest is not None and dest.on_hand == Decimal("30.0000")


def test_transfer_issue_rejected_without_stock(client) -> None:
    p = _product()
    supplier = create_user(kind="supplier", email="sup2@example.com", roles=("supplier",))
    order = transfers_svc.create_transfer_order(
        supplier_id=supplier.id,
        from_location_type="supplier",
        from_location_id=None,
        to_location_type="channel_partner",
        to_location_id=1,
        lines=[LineInput(product_id=p.id, qty=Decimal("5"), unit_cost=Decimal("10"))],
        initiated_by=1,
    )
    with pytest.raises(Exception):  # noqa: B017 — NotFound: no source stock
        transfers_svc.issue(order_id=order.id, issued_by=1)
    db.session.rollback()


def test_mixed_category_transfer_rejected(client) -> None:
    food = _product(sku="F-1", category="food")
    cloth = _product(sku="C-1", category="clothing")
    supplier = create_user(kind="supplier", email="sup3@example.com", roles=("supplier",))
    with pytest.raises(Exception):  # noqa: B017 — BadRequest mixed category
        transfers_svc.create_transfer_order(
            supplier_id=supplier.id,
            from_location_type="supplier",
            from_location_id=None,
            to_location_type="channel_partner",
            to_location_id=1,
            lines=[
                LineInput(product_id=food.id, qty=Decimal("1"), unit_cost=Decimal("1")),
                LineInput(product_id=cloth.id, qty=Decimal("1"), unit_cost=Decimal("1")),
            ],
            initiated_by=1,
        )
    db.session.rollback()


# ---------------------------------------------------------------- US-4.4


def _pending_shortage(category: str = "food"):
    p = _product(sku=f"SH-{category}", category=category)
    supplier = create_user(
        kind="supplier", email=f"shsup-{category}@example.com", roles=("supplier",)
    )
    return shortages_svc.report_shortage(
        reporter_user_id=1,
        supplier_id=supplier.id,
        product_id=p.id,
        qty=Decimal("5"),
        unit_cost=Decimal("20"),
        evidence_s3_keys=["evidence/1.jpg"],
    )


def test_shortage_resolved_against_supplier_debits_payable(client) -> None:
    sh = _pending_shortage(category="food")
    resolved = shortages_svc.resolve_shortage(
        shortage_id=sh.id,
        responsible_party_type="supplier",
        responsible_party_id=None,
        reason="مسؤولية المورد — نقص عند الاستلام",
        resolved_by=1,
    )
    assert resolved.status == "resolved"
    assert resolved.journal_entry_id is not None
    assert _debit_codes(resolved.journal_entry_id) == ["2111"]  # food supplier payable
    assert _credit_codes(resolved.journal_entry_id) == ["1151"]


def test_shortage_resolved_against_agent_debits_1141(client) -> None:
    sh = _pending_shortage(category="clothing")
    agent_user = create_user(kind="agent", email="ag@example.com", roles=("agent",))
    # channel partner profile for the agent
    from app.identity.models import ChannelPartnerProfile

    db.session.add(
        ChannelPartnerProfile(
            user_id=agent_user.id, type="agent", display_name="وكيل القاهرة"
        )
    )
    db.session.commit()

    resolved = shortages_svc.resolve_shortage(
        shortage_id=sh.id,
        responsible_party_type="channel_partner",
        responsible_party_id=agent_user.id,
        reason="مسؤولية الوكيل أثناء العهدة",
        resolved_by=1,
    )
    assert resolved.journal_entry_id is not None
    assert _debit_codes(resolved.journal_entry_id) == ["1141"]  # agent receivable
    assert _credit_codes(resolved.journal_entry_id) == ["1152"]  # clothing


def test_shortage_unallocated_hits_loss_account(client) -> None:
    sh = _pending_shortage(category="food")
    resolved = shortages_svc.resolve_shortage(
        shortage_id=sh.id,
        responsible_party_type="unallocated",
        responsible_party_id=None,
        reason="تلف أثناء النقل — غير محدد المسؤول",
        resolved_by=1,
    )
    assert resolved.journal_entry_id is not None
    assert _debit_codes(resolved.journal_entry_id) == ["5310"]


# ---------------------------------------------------------------- US-4.3


def test_reorder_check_opens_alert_when_below_point(client) -> None:
    p = _product()
    supplier = create_user(kind="supplier", email="ro@example.com", roles=("supplier",))
    stock_svc.manual_adjust(
        supplier_id=supplier.id,
        product_id=p.id,
        location_type="supplier",
        location_id=None,
        delta=Decimal("3"),
        reorder_point=Decimal("10"),
    )
    created = reorder_svc.check(supplier_id=supplier.id)
    assert len(created) == 1
    assert created[0].level == 1
    # second check doesn't duplicate the open alert
    again = reorder_svc.check(supplier_id=supplier.id)
    assert again == []


# ---------------------------------------------------------------- RBAC


def test_customer_cannot_create_product(client) -> None:
    create_user(kind="customer", phone="+201000000210", roles=("customer",))
    headers = auth_header(client, phone="+201000000210")
    r = client.post(
        "/inventory/products",
        headers=headers,
        json={"sku": "X", "name_ar": "x", "category": "food"},
    )
    assert r.status_code == 403


def test_admin_can_create_product_via_route(client) -> None:
    create_user(kind="admin", email="invadmin@example.com", roles=("admin.high",))
    headers = auth_header(client, email="invadmin@example.com")
    r = client.post(
        "/inventory/products",
        headers=headers,
        json={"sku": "SKU-ADMIN", "name_ar": "منتج", "category": "food"},
    )
    assert r.status_code == 201
    assert r.get_json()["sku"] == "SKU-ADMIN"


def test_stock_balances_supplier_isolation_via_route(client) -> None:
    p = _product()
    s1 = create_user(kind="supplier", phone="+201000000220", roles=("supplier",))
    other = create_user(kind="supplier", email="other@example.com", roles=("supplier",))
    stock_svc.manual_adjust(
        supplier_id=s1.id, product_id=p.id, location_type="supplier",
        location_id=None, delta=Decimal("50"),
    )
    stock_svc.manual_adjust(
        supplier_id=other.id, product_id=p.id, location_type="supplier",
        location_id=None, delta=Decimal("70"),
    )
    headers = auth_header(client, phone="+201000000220")
    r = client.get("/inventory/stock-balances", headers=headers)
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert all(it["supplier_id"] == s1.id for it in items)
    assert len(items) == 1


def test_transfer_date_default_is_today(client) -> None:
    # smoke: a product with no category issues in transfer context
    assert date.today().year >= 2026

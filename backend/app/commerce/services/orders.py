"""Checkout → unified order split into per-supplier sub-orders (US-1.2),
priced at the locked prices (US-1.6), with the auto double-entry journal
(order.placed.cash / order.placed.deferred) per category.

For deferred orders the whole-order spread (deferred_total − cash_total) is
allocated across categories in proportion to each category's cash share, and
a single Shariah-compliant `accounting.deferred_terms` row is created.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from ...accounting.services import deferred as deferred_svc
from ...accounting.services import events as journal
from ...common.errors import BadRequest
from ...common.money import to_money
from ...extensions import db
from ...inventory.models import Product, SupplierOffer
from ..models import Cart, Order, OrderLine, OrderSubOrder
from . import pricelock


def _number() -> str:
    return f"ORD-{datetime.now(UTC).strftime('%Y%m')}-"


def checkout(  # noqa: PLR0912 — cash/deferred × per-category × per-supplier flow
    *,
    customer_id: int,
    payment_mode: str,
    deferred_total: Decimal | None = None,
    early_settlement_discount: Decimal | None = None,
    early_settlement_before: date | None = None,
    entry_date: date | None = None,
) -> Order:
    if payment_mode not in ("cash", "deferred"):
        raise BadRequest("payment_mode must be cash|deferred", code="bad_payment_mode")

    cart = db.session.execute(
        select(Cart).where(Cart.customer_id == customer_id, Cart.status == "active")
    ).scalar_one_or_none()
    if cart is None or not cart.items:
        raise BadRequest("السلة فارغة", code="empty_cart")

    # Resolve each item's locked price + supplier + category.
    by_supplier: dict[int, list[tuple[Any, Decimal, Decimal]]] = defaultdict(list)
    cash_by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    total_cash = Decimal("0")

    for item in cart.items:
        offer = db.session.get(SupplierOffer, item.supplier_offer_id)
        product = db.session.get(Product, item.product_id)
        assert offer is not None and product is not None
        lock = pricelock.lock_for_cart_item(item.id)
        unit_price = to_money(lock.locked_price) if lock is not None else to_money(offer.unit_price)
        line_total = to_money(item.qty) * unit_price
        by_supplier[offer.supplier_id].append((item, unit_price, line_total))
        cash_by_category[product.category] += line_total
        total_cash += line_total

    if payment_mode == "deferred":
        if deferred_total is None:
            raise BadRequest("deferred_total required for deferred orders", code="deferred_total_required")
        d_total = to_money(deferred_total)
        if d_total < total_cash:
            raise BadRequest("deferred_total must be ≥ cash total", code="deferred_lt_cash")
    else:
        d_total = total_cash

    # Create the order shell.
    order = Order(
        number="PENDING",
        customer_id=customer_id,
        status="pending",
        payment_mode=payment_mode,
        total_cash=total_cash,
        total_deferred=d_total,
        credit_check_at=datetime.now(UTC),  # hook; full credit logic = Phase 6
    )
    db.session.add(order)
    db.session.flush()
    order.number = f"{_number()}{order.id:06d}"

    # Per-supplier sub-orders + lines.
    for supplier_id, rows in by_supplier.items():
        subtotal = sum((lt for (_i, _p, lt) in rows), start=Decimal("0"))
        sub = OrderSubOrder(order_id=order.id, supplier_id=supplier_id, status="pending", subtotal=subtotal)
        db.session.add(sub)
        db.session.flush()
        for item, unit_price, line_total in rows:
            db.session.add(
                OrderLine(
                    sub_order_id=sub.id,
                    product_id=item.product_id,
                    supplier_offer_id=item.supplier_offer_id,
                    qty=to_money(item.qty),
                    unit_price=unit_price,
                    line_total=line_total,
                )
            )

    # Journals — one per category.
    total_spread = d_total - total_cash
    first_entry_id: int | None = None
    for category, cat_cash in cash_by_category.items():
        if payment_mode == "cash":
            posting = journal.post(
                event_type="order.placed.cash",
                entry_date=entry_date or date.today(),
                description=f"طلب {order.number} — {category}",
                context={"amount": cat_cash, "category": category},
                source_event_id=order.id,
            )
        else:
            cat_spread = (
                (total_spread * cat_cash / total_cash) if total_cash > 0 else Decimal("0")
            )
            posting = journal.post(
                event_type="order.placed.deferred",
                entry_date=entry_date or date.today(),
                description=f"طلب آجل {order.number} — {category}",
                context={
                    "cash_price": cat_cash,
                    "deferred_price": cat_cash + cat_spread,
                    "spread": cat_spread,
                    "category": category,
                },
                source_event_id=order.id,
            )
        if first_entry_id is None:
            first_entry_id = posting.entry_id
    order.journal_entry_id = first_entry_id

    # Deferred terms (Shariah) for the whole order.
    if payment_mode == "deferred":
        deferred_svc.create(
            order_id=order.id,
            cash_price=total_cash,
            deferred_price=d_total,
            early_settlement_discount=early_settlement_discount or Decimal("0"),
            early_settlement_before=early_settlement_before,
        )

    # Consume the price locks and close the cart.
    for item in cart.items:
        pricelock.consume_lock_for_cart_item(item.id)
    cart.status = "checked_out"
    db.session.commit()
    return order


def list_orders(customer_id: int, limit: int = 50) -> list[Order]:
    stmt = (
        select(Order)
        .where(Order.customer_id == customer_id)
        .order_by(Order.id.desc())
        .limit(limit)
    )
    return list(db.session.execute(stmt).scalars().all())


def serialize_order(order: Order, *, for_customer: bool) -> dict[str, Any]:
    """Customer view hides suppliers; admin view includes sub-order suppliers."""
    base: dict[str, Any] = {
        "id": order.id,
        "number": order.number,
        "status": order.status,
        "payment_mode": order.payment_mode,
        "total_cash": str(order.total_cash),
        "total_deferred": str(order.total_deferred),
        "placed_at": order.placed_at.isoformat(),
    }
    if for_customer:
        # No supplier breakdown — just the lines merged.
        lines: list[dict[str, Any]] = []
        for sub in order.sub_orders:
            for ln in sub.lines:
                lines.append(
                    {
                        "product_id": ln.product_id,
                        "qty": str(ln.qty),
                        "unit_price": str(ln.unit_price),
                        "line_total": str(ln.line_total),
                    }
                )
        base["lines"] = lines
    else:
        base["sub_orders"] = [
            {
                "id": sub.id,
                "supplier_id": sub.supplier_id,
                "subtotal": str(sub.subtotal),
                "lines": [
                    {
                        "product_id": ln.product_id,
                        "supplier_offer_id": ln.supplier_offer_id,
                        "qty": str(ln.qty),
                        "unit_price": str(ln.unit_price),
                        "line_total": str(ln.line_total),
                    }
                    for ln in sub.lines
                ],
            }
            for sub in order.sub_orders
        ]
    return base

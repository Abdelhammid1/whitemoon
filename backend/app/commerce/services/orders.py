"""Checkout → unified order split into per-supplier sub-orders (US-1.2),
priced at the locked prices (US-1.6), with the auto double-entry journal
(order.placed.cash / order.placed.deferred) per category.

For deferred orders the whole-order spread (deferred_total − cash_total) is
allocated across categories in proportion to each category's cash share, and
a single Shariah-compliant `accounting.deferred_terms` row is created.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
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

# Deferred-pricing schedule — PLACEHOLDER values pending a schedule signed by
# the finance lead (same rule as the Chart of Accounts / credit rules: a
# business rule, never customer input nor developer discretion in prod).
# docs/03-journal-map.md §2 + docs/04 note these must be approved before go-live.
DEFERRED_MARKUP_PCT = Decimal("0.10")  # deferred_total = cash × (1 + markup)
EARLY_DISCOUNT_PCT = Decimal("0.50")  # discount = spread × pct (0 ≤ disc < spread)
EARLY_WINDOW_DAYS = 14
CREDIT_NET_DAYS = 30  # deferred payment due date = placed + net days


def _number() -> str:
    return f"ORD-{datetime.now(UTC).strftime('%Y%m')}-"


def checkout(  # noqa: PLR0912, PLR0915 — cash/deferred × per-category × per-supplier
    *,
    customer_id: int,
    payment_mode: str,
    entry_date: date | None = None,
) -> Order:
    """Place the active cart. Financial terms (deferred price, discount,
    window) are computed SERVER-SIDE from the approved schedule — never taken
    from the client (US-3.4)."""
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
        if not offer.is_active:
            raise BadRequest(
                f"عرض لم يعد متاحًا في السلة (منتج {item.product_id})",
                code="offer_unavailable",
            )
        # Honour a LIVE lock only; an expired hold reverts to the live price.
        lock = pricelock.lock_for_cart_item(item.id)
        unit_price = to_money(lock.locked_price) if lock is not None else to_money(offer.unit_price)
        line_total = to_money(item.qty) * unit_price
        by_supplier[offer.supplier_id].append((item, unit_price, line_total))
        cash_by_category[product.category] += line_total
        total_cash += line_total

    # Per-supplier minimum order value (US-4.5, T-03): block the checkout if
    # any supplier's sub-order total is below that supplier's minimum. The
    # supplier is never named (customer-supplier isolation).
    from ...identity.models import SupplierProfile

    for supplier_id, rows in by_supplier.items():
        sub_total = sum((lt for (_i, _u, lt) in rows), start=Decimal("0"))
        prof = db.session.get(SupplierProfile, supplier_id)
        minimum = to_money(prof.min_order_value) if prof is not None else Decimal("0")
        if minimum > 0 and sub_total < minimum:
            raise BadRequest(
                f"قيمة الطلب من أحد الموردين أقل من الحد الأدنى ({minimum} ج.م)",
                code="below_supplier_minimum",
            )

    # Deferred terms are SERVER-COMPUTED from the approved schedule.
    if payment_mode == "deferred":
        d_total = to_money(total_cash * (Decimal("1") + DEFERRED_MARKUP_PCT))
        spread = d_total - total_cash
        discount = to_money(spread * EARLY_DISCOUNT_PCT)
        before = date.today() + timedelta(days=EARLY_WINDOW_DAYS)
    else:
        d_total = total_cash
        discount = Decimal("0")
        before = None

    # Credit control (US-5.2): block a deferred order that would exceed the
    # customer's limit, and reject deferred entirely for a red-tier customer.
    from ...sales.services import credit as credit_svc

    credit_svc.check_credit(
        customer_id=customer_id, order_amount=d_total, deferred=(payment_mode == "deferred")
    )

    # Create the order shell.
    order = Order(
        number="PENDING",
        customer_id=customer_id,
        status="pending",
        payment_mode=payment_mode,
        total_cash=total_cash,
        total_deferred=d_total,
        credit_check_at=datetime.now(UTC),
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
            early_settlement_discount=discount,
            early_settlement_before=before,
        )
        # Record the receivable that feeds the credit algorithm (US-5.1/5.3).
        credit_svc.record_due(
            customer_id=customer_id,
            order_id=order.id,
            amount=d_total,
            due_date=date.today() + timedelta(days=CREDIT_NET_DAYS),
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


def supplier_dashboard(supplier_id: int, limit: int = 100) -> list[dict[str, Any]]:
    """A supplier's own sub-orders with the parent order's live status (T-06).
    No customer PII — the supplier sees order number, status, their lines."""
    stmt = (
        select(OrderSubOrder, Order)
        .join(Order, Order.id == OrderSubOrder.order_id)
        .where(OrderSubOrder.supplier_id == supplier_id)
        .order_by(OrderSubOrder.id.desc())
        .limit(limit)
    )
    rows = db.session.execute(stmt).all()
    out: list[dict[str, Any]] = []
    for sub, order in rows:
        out.append(
            {
                "sub_order_id": sub.id,
                "order_number": order.number,
                "order_status": order.status,
                "sub_order_status": sub.status,
                "subtotal": str(sub.subtotal),
                "placed_at": order.placed_at.isoformat(),
                "lines": [
                    {
                        "product_id": ln.product_id,
                        "qty": str(ln.qty),
                        "unit_price": str(ln.unit_price),
                        "line_total": str(ln.line_total),
                    }
                    for ln in sub.lines
                ],
            }
        )
    return out


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

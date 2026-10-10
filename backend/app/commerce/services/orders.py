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

from sqlalchemy import func, select

from ...accounting.services import deferred as deferred_svc
from ...accounting.services import events as journal
from ...common.errors import BadRequest, Conflict, Forbidden, NotFound
from ...common.money import to_money
from ...extensions import db
from ...inventory.models import Product, SupplierOffer
from ..models import Cart, Order, OrderLine, OrderSubOrder
from . import pricelock

# Deferred pricing is now a configurable annual-rate engine (T-28): the fee,
# duration, and per-tier/per-customer rate come from `sales.deferred_settings`
# via `deferred_pricing`, never a code constant. Only the early-settlement
# discount shape stays here (a fixed fraction of the fee, within a window).
EARLY_DISCOUNT_PCT = Decimal("0.50")  # discount = spread × pct (0 ≤ disc < spread)
EARLY_WINDOW_DAYS = 14


def _number() -> str:
    return f"ORD-{datetime.now(UTC).strftime('%Y%m')}-"


def checkout(  # noqa: PLR0912, PLR0915 — cash/deferred × per-category × per-supplier
    *,
    customer_id: int,
    payment_mode: str,
    deferred_days: int | None = None,
    entry_date: date | None = None,
) -> Order:
    """Place the active cart. Financial terms (annual rate, fee, discount,
    window) are computed SERVER-SIDE from the approved schedule (T-28) — never
    taken from the client (US-3.4). For a deferred order the customer only
    chooses a duration (`deferred_days`), validated against the allowed/max
    days; the rate and fee are resolved from the deferred-pricing settings."""
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

    # Deferred terms are SERVER-COMPUTED from the configurable schedule (T-28):
    # the annual rate resolves per customer/tier, and the fee is proportional to
    # the chosen duration. A red customer (resolve → None) is blocked below by
    # check_credit, consistent with the credit rules.
    from ...sales.services import deferred_pricing as deferred_pricing_svc

    annual_pct: Decimal | None = None
    deferred_days_used = 0
    if payment_mode == "deferred":
        annual_pct = deferred_pricing_svc.resolve_annual_pct(customer_id)
        if annual_pct is None:
            raise Forbidden("التصنيف الأحمر لا يسمح بالبيع الآجل — نقدي فقط", code="deferred_blocked_red")
        s = deferred_pricing_svc.get_settings()
        deferred_days_used = deferred_pricing_svc.validate_days(deferred_days or s.default_days)
        fee = deferred_pricing_svc.compute_fee(total_cash, annual_pct, deferred_days_used)
        d_total = to_money(total_cash + fee)
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

    # Deferred terms (Shariah) for the whole order, with the T-28 snapshot of
    # the annual rate / duration / fee so a later rate change never alters a
    # placed order.
    if payment_mode == "deferred":
        term = deferred_svc.create(
            order_id=order.id,
            cash_price=total_cash,
            deferred_price=d_total,
            early_settlement_discount=discount,
            early_settlement_before=before,
        )
        term.annual_pct = annual_pct
        term.days = deferred_days_used
        term.fee = to_money(d_total - total_cash)
        # Record the receivable that feeds the credit algorithm (US-5.1/5.3),
        # due on placed + the chosen duration.
        credit_svc.record_due(
            customer_id=customer_id,
            order_id=order.id,
            amount=d_total,
            due_date=date.today() + timedelta(days=deferred_days_used),
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


# Admin order lifecycle (T-13): action -> (allowed-from, order-to, sub-order-to).
_ORDER_TRANSITIONS: dict[str, tuple[set[str], str, str]] = {
    "confirm": ({"pending"}, "confirmed", "confirmed"),
    "fulfill": ({"confirmed"}, "fulfilled", "preparing"),
    "cancel": ({"pending", "confirmed"}, "cancelled", "cancelled"),
}


def list_all_orders(
    *,
    status: str | None = None,
    customer_id: int | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 200,
) -> list[Order]:
    """Admin/staff view of every order with search + status/customer/date
    filters (T-13). Not customer-scoped."""
    stmt = select(Order).order_by(Order.id.desc()).limit(limit)
    if status:
        stmt = stmt.where(Order.status == status)
    if customer_id:
        stmt = stmt.where(Order.customer_id == customer_id)
    if q:
        stmt = stmt.where(Order.number.ilike(f"%{q}%"))

    def _parse(label: str, s: str) -> date:
        try:
            return date.fromisoformat(s)
        except ValueError as e:
            raise BadRequest(f"{label} يجب أن يكون بصيغة YYYY-MM-DD", code="bad_date") from e

    if date_from:
        stmt = stmt.where(func.date(Order.placed_at) >= _parse("date_from", date_from))
    if date_to:
        stmt = stmt.where(func.date(Order.placed_at) <= _parse("date_to", date_to))
    return list(db.session.execute(stmt).scalars().all())


def serialize_admin_rows(orders: list[Order]) -> list[dict[str, Any]]:
    """Light list rows (no sub-order/line breakdown) with batch-loaded customer
    names — for the admin orders table (T-13)."""
    from ...identity.models import CustomerProfile

    ids = {o.customer_id for o in orders}
    names: dict[int, str] = {}
    if ids:
        rows = db.session.execute(
            select(CustomerProfile.user_id, CustomerProfile.display_name).where(
                CustomerProfile.user_id.in_(ids)
            )
        ).all()
        names = {uid: name for uid, name in rows}
    return [
        {
            "id": o.id,
            "number": o.number,
            "status": o.status,
            "payment_mode": o.payment_mode,
            "total_cash": str(o.total_cash),
            "total_deferred": str(o.total_deferred),
            "placed_at": o.placed_at.isoformat(),
            "customer_id": o.customer_id,
            "customer_name": names.get(o.customer_id),
        }
        for o in orders
    ]


def serialize_admin(order: Order) -> dict[str, Any]:
    """Admin order view: full sub-order/supplier breakdown + the customer."""
    from ...identity.models import CustomerProfile

    d = serialize_order(order, for_customer=False)
    d["customer_id"] = order.customer_id
    prof = db.session.get(CustomerProfile, order.customer_id)
    d["customer_name"] = prof.display_name if prof else None
    return d


def transition_order(order_id: int, action: str, *, actor_id: int | None = None) -> Order:
    """Confirm / fulfill (prepare) / cancel an order and propagate the status to
    its per-supplier sub-orders so suppliers see the change (T-13). Cancelling
    also backs out the order's financials (GL reversal, voided due, closed
    deferred terms) so a cancelled order leaves nothing owed."""
    rule = _ORDER_TRANSITIONS.get(action)
    if rule is None:
        raise Conflict(f"إجراء غير معروف: {action}", code="bad_action")
    # Lock the order row so two concurrent transitions can't both pass the
    # status check and double-process (e.g. reverse the GL twice on cancel).
    order = db.session.get(Order, order_id, with_for_update=True)
    if order is None:
        raise NotFound("Order not found", code="order_not_found")
    allowed_from, order_to, sub_to = rule
    if order.status not in allowed_from:
        raise Conflict(
            f"لا يمكن تنفيذ «{action}» على طلب حالته «{order.status}»", code="bad_transition"
        )
    if action == "cancel":
        _reverse_order_financials(order, posted_by=actor_id)
    order.status = order_to
    for sub in order.sub_orders:
        sub.status = sub_to
    db.session.commit()
    return order


def _reverse_order_financials(order: Order, *, posted_by: int | None) -> None:
    """On cancel: reverse the order's GL entry, void its open due, and close any
    deferred-terms row — so no receivable/revenue lingers."""
    from ...accounting.models import DeferredTerm
    from ...accounting.services import events as journal
    from ...sales.models import CustomerDue

    if order.journal_entry_id:
        journal.reverse(
            order.journal_entry_id, reason=f"إلغاء الطلب {order.number}", posted_by=posted_by
        )
    dues = db.session.execute(
        select(CustomerDue).where(
            CustomerDue.order_id == order.id, CustomerDue.status == "open"
        )
    ).scalars().all()
    for d in dues:
        d.status = "cancelled"
    dt = db.session.execute(
        select(DeferredTerm).where(DeferredTerm.order_id == order.id)
    ).scalar_one_or_none()
    if dt is not None and dt.settled_at is None:
        dt.settled_at = datetime.now(UTC)


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

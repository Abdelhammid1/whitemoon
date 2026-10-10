"""Customer shopping helpers: reorder + usual items (T-42) and usual
categories (T-32). All read the customer's own order history; prices are always
resolved LIVE from the current best offer (never the historical price)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from ...common.errors import Conflict, NotFound
from ...common.money import to_money
from ...extensions import db
from ...inventory.models import Product
from ...settings import service as settings
from ..models import Order, OrderLine, OrderSubOrder
from . import cart as cart_svc
from . import catalog as catalog_svc

_EXCLUDED_ORDER_STATUSES = ("cancelled",)


def _customer_line_totals(customer_id: int):
    """Per-product aggregates over the customer's non-cancelled orders:
    (product_id, total_qty, line_count, last_unit_price)."""
    return db.session.execute(
        select(
            OrderLine.product_id,
            func.sum(OrderLine.qty).label("total_qty"),
            func.count().label("line_count"),
        )
        .join(OrderSubOrder, OrderSubOrder.id == OrderLine.sub_order_id)
        .join(Order, Order.id == OrderSubOrder.order_id)
        .where(Order.customer_id == customer_id, Order.status.notin_(_EXCLUDED_ORDER_STATUSES))
        .group_by(OrderLine.product_id)
    ).all()


def reorder(*, customer_id: int, order_id: int) -> dict[str, Any]:
    """Add a past order's items to the active cart at CURRENT prices (T-42).
    Returns what was added and warnings for items whose price changed, that are
    out of stock, or already in the cart."""
    order = db.session.get(Order, order_id)
    if order is None or order.customer_id != customer_id:
        raise NotFound("الطلب غير موجود", code="order_not_found")

    # Aggregate the order's lines per product (qty summed, original price kept).
    wanted: dict[int, dict[str, Any]] = {}
    for sub in order.sub_orders:
        for ln in sub.lines:
            w = wanted.setdefault(ln.product_id, {"qty": Decimal("0"), "orig": to_money(ln.unit_price)})
            w["qty"] += to_money(ln.qty)

    added = 0
    warnings: list[dict[str, Any]] = []
    for product_id, w in wanted.items():
        best = catalog_svc.get_product(product_id)
        if best is None or best["best_offer_id"] is None:
            warnings.append({"product_id": product_id, "reason": "unavailable"})
            continue
        new_price = to_money(best["best_price"])
        if new_price != w["orig"]:
            warnings.append({
                "product_id": product_id, "reason": "price_changed",
                "old_price": str(w["orig"]), "new_price": str(new_price),
            })
        try:
            cart_svc.add_item(customer_id=customer_id, offer_id=best["best_offer_id"], qty=w["qty"])
            added += 1
        except Conflict:
            warnings.append({"product_id": product_id, "reason": "already_in_cart"})
        except Exception:
            # e.g. below the current MOQ — surface it without failing the whole reorder.
            warnings.append({"product_id": product_id, "reason": "could_not_add"})
    return {"added": added, "warnings": warnings}


def usual_items(*, customer_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """The customer's most-frequently-ordered products with their usual qty and
    the CURRENT best price, addable in one click (T-42). Only items still
    buyable (an active offer) are returned."""
    rows = sorted(_customer_line_totals(customer_id), key=lambda r: (r.line_count, r.total_qty), reverse=True)
    out: list[dict[str, Any]] = []
    for r in rows:
        if len(out) >= limit:
            break
        best = catalog_svc.get_product(r.product_id)
        if best is None or best["best_offer_id"] is None:
            continue
        # Usual qty = rounded average per appearance (at least 1).
        usual_qty = to_money(r.total_qty) / Decimal(r.line_count) if r.line_count else Decimal("1")
        out.append({
            "product_id": r.product_id,
            "name_ar": best["name_ar"],
            "image_url": best["image_url"],
            "best_price": best["best_price"],
            "best_offer_id": best["best_offer_id"],
            "usual_qty": str(usual_qty.quantize(Decimal("0.01"))),
        })
    return out


def usual_categories(*, customer_id: int, limit: int = 8) -> list[dict[str, Any]]:
    """The categories the customer buys from most over the last N days (T-32;
    N = `customer.usual_window_days`, tunable in «إعدادات النظام» — T-37).
    A new customer (no history) falls back to the platform's most-ordered
    categories («الأكثر طلبًا»)."""
    cutoff = datetime.now(UTC) - timedelta(days=settings.get_int("customer.usual_window_days"))
    base = (
        select(Product.category, func.count().label("n"))
        .join(OrderLine, OrderLine.product_id == Product.id)
        .join(OrderSubOrder, OrderSubOrder.id == OrderLine.sub_order_id)
        .join(Order, Order.id == OrderSubOrder.order_id)
        .where(Order.status.notin_(_EXCLUDED_ORDER_STATUSES), Order.placed_at >= cutoff)
        .group_by(Product.category)
        .order_by(func.count().desc())
        .limit(limit)
    )
    mine = db.session.execute(base.where(Order.customer_id == customer_id)).all()
    fallback = False
    rows = mine
    if not rows:
        rows = db.session.execute(base).all()  # platform-wide «الأكثر طلبًا»
        fallback = True
    return [{"category": c, "count": int(n), "fallback": fallback} for c, n in rows]

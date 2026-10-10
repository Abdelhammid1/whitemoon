"""Supplier action dashboard (T-41): the three "needs action now" lists —
new sub-orders awaiting confirmation, items near depletion, discounts ending
soon — plus the supplier's quick confirm / ready actions on their own
sub-orders."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from ...common.errors import Conflict, Forbidden, NotFound
from ...common.money import to_money
from ...extensions import db
from ...inventory.models import Product, StockBalance, SupplierOffer
from ..models import Order, OrderSubOrder

DISCOUNT_EXPIRY_SOON_DAYS = 7

# Supplier-driven sub-order transitions (parallel to the admin order lifecycle):
# the supplier acknowledges their part, then marks it ready for handover.
_SUPPLIER_SUBORDER_TRANSITIONS: dict[str, tuple[set[str], str]] = {
    "confirm": ({"pending"}, "confirmed"),
    "ready": ({"confirmed", "preparing"}, "ready"),
}


def action_summary(supplier_id: int) -> dict[str, Any]:
    """The supplier home's three cards."""
    # 1) New sub-orders awaiting the supplier's confirmation.
    new_rows = db.session.execute(
        select(OrderSubOrder, Order)
        .join(Order, Order.id == OrderSubOrder.order_id)
        .where(OrderSubOrder.supplier_id == supplier_id, OrderSubOrder.status == "pending")
        .order_by(OrderSubOrder.id.desc())
        .limit(50)
    ).all()
    new_orders = [
        {
            "sub_order_id": sub.id,
            "order_number": order.number,
            "status": sub.status,
            "subtotal": str(sub.subtotal),
            "placed_at": order.placed_at.isoformat(),
        }
        for sub, order in new_rows
    ]

    # 2) Items near depletion (on_hand at/below the reorder point).
    low_rows = db.session.execute(
        select(StockBalance, Product.name_ar)
        .join(Product, Product.id == StockBalance.product_id)
        .where(
            StockBalance.supplier_id == supplier_id,
            StockBalance.reorder_point.isnot(None),
            StockBalance.on_hand <= StockBalance.reorder_point,
        )
        .order_by(StockBalance.on_hand.asc())
        .limit(50)
    ).all()
    low_stock = [
        {
            "product_id": b.product_id,
            "name": name,
            "on_hand": str(to_money(b.on_hand)),
            "reorder_point": str(to_money(b.reorder_point)) if b.reorder_point is not None else None,
        }
        for b, name in low_rows
    ]

    # 3) Discounts ending soon.
    soon = date.today() + timedelta(days=DISCOUNT_EXPIRY_SOON_DAYS)
    disc_rows = db.session.execute(
        select(SupplierOffer, Product.name_ar)
        .join(Product, Product.id == SupplierOffer.product_id)
        .where(
            SupplierOffer.supplier_id == supplier_id,
            SupplierOffer.discount_kind != "none",
            SupplierOffer.discount_end.isnot(None),
            SupplierOffer.discount_end <= soon,
            SupplierOffer.discount_end >= date.today(),
        )
        .order_by(SupplierOffer.discount_end.asc())
        .limit(50)
    ).all()
    expiring_discounts = [
        {
            "product_id": o.product_id,
            "name": name,
            "discount_end": o.discount_end.isoformat() if o.discount_end else None,
        }
        for o, name in disc_rows
    ]

    return {
        "new_orders": new_orders,
        "low_stock": low_stock,
        "expiring_discounts": expiring_discounts,
        "counts": {
            "new_orders": len(new_orders),
            "low_stock": len(low_stock),
            "expiring_discounts": len(expiring_discounts),
        },
    }


def advance_suborder(*, supplier_id: int, sub_order_id: int, action: str) -> OrderSubOrder:
    """A supplier confirms, or marks ready, THEIR OWN sub-order (T-41)."""
    rule = _SUPPLIER_SUBORDER_TRANSITIONS.get(action)
    if rule is None:
        raise Conflict(f"إجراء غير معروف: {action}", code="bad_action")
    sub = db.session.get(OrderSubOrder, sub_order_id, with_for_update=True)
    if sub is None:
        raise NotFound("الطلب الفرعي غير موجود", code="sub_order_not_found")
    if sub.supplier_id != supplier_id:
        raise Forbidden("ليس طلبك الفرعي", code="forbidden")
    allowed_from, to = rule
    if sub.status not in allowed_from:
        raise Conflict(
            f"لا يمكن تنفيذ «{action}» على حالة «{sub.status}»", code="bad_transition"
        )
    sub.status = to
    db.session.commit()
    return sub

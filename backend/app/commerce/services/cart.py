"""Unified multi-supplier cart (US-1.2) with price-lock on add (US-1.6).

Customer-facing serialization never exposes the supplier behind an item.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select

from ...common.errors import BadRequest, Conflict, NotFound
from ...common.money import to_money
from ...extensions import db
from ...inventory.models import Product, SupplierOffer
from ...inventory.services import offers as offers_svc
from ..models import Cart, CartItem
from . import pricelock


def get_or_create_active_cart(customer_id: int) -> Cart:
    cart = db.session.execute(
        select(Cart).where(Cart.customer_id == customer_id, Cart.status == "active")
    ).scalar_one_or_none()
    if cart is None:
        cart = Cart(customer_id=customer_id, status="active")
        db.session.add(cart)
        db.session.flush()
    return cart


def add_item(*, customer_id: int, offer_id: int, qty: Decimal) -> CartItem:
    offer = db.session.get(SupplierOffer, offer_id)
    if offer is None or not offer.is_active:
        raise NotFound("Offer not found or inactive", code="offer_unavailable")
    if to_money(qty) < to_money(offer.moq):
        raise BadRequest(
            f"الكمية أقل من الحد الأدنى للطلب ({offer.moq})", code="below_moq"
        )

    cart = get_or_create_active_cart(customer_id)
    existing = db.session.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id, CartItem.supplier_offer_id == offer_id
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise Conflict("الصنف موجود بالسلة؛ عدّل الكمية بدلاً من ذلك", code="item_exists")

    item = CartItem(
        cart_id=cart.id,
        product_id=offer.product_id,
        supplier_offer_id=offer_id,
        qty=to_money(qty),
    )
    db.session.add(item)
    db.session.flush()
    # Lock the current EFFECTIVE price (honouring an active discount) for the
    # reserved quantity (T-30).
    pricelock.create_lock(
        offer_id=offer_id, cart_item_id=item.id, qty=qty, price=offers_svc.effective_price(offer)
    )
    db.session.commit()
    return item


def update_qty(*, customer_id: int, item_id: int, qty: Decimal) -> CartItem:
    item = _owned_item(customer_id, item_id)
    offer = db.session.get(SupplierOffer, item.supplier_offer_id)
    assert offer is not None
    if to_money(qty) < to_money(offer.moq):
        raise BadRequest(f"الكمية أقل من الحد الأدنى ({offer.moq})", code="below_moq")
    if not offer.is_active:
        raise Conflict("العرض لم يعد متاحًا", code="offer_unavailable")
    new_qty = to_money(qty)
    item.qty = new_qty
    # Re-lock. Honour the held price ONLY while the lock is still live AND the
    # new quantity does not exceed what was reserved; otherwise lock at the
    # supplier's current price (the hold is for the originally reserved qty).
    lock = pricelock.lock_for_cart_item(item.id)
    if lock is not None and new_qty <= to_money(lock.locked_qty):
        locked_price = lock.locked_price
    else:
        locked_price = offers_svc.effective_price(offer)
    pricelock.release_lock_for_cart_item(item.id)
    pricelock.create_lock(offer_id=offer.id, cart_item_id=item.id, qty=new_qty, price=locked_price)
    db.session.commit()
    return item


def remove_item(*, customer_id: int, item_id: int) -> None:
    item = _owned_item(customer_id, item_id)
    pricelock.release_lock_for_cart_item(item.id)
    db.session.delete(item)
    db.session.commit()


def _owned_item(customer_id: int, item_id: int) -> CartItem:
    item = db.session.get(CartItem, item_id)
    if item is None:
        raise NotFound("Cart item not found", code="item_not_found")
    cart = db.session.get(Cart, item.cart_id)
    if cart is None or cart.customer_id != customer_id:
        raise NotFound("Cart item not found", code="item_not_found")
    return item


def serialize_cart(customer_id: int) -> dict[str, Any]:
    """Customer view — shows locked price per item, totals, NO supplier id."""
    cart = get_or_create_active_cart(customer_id)
    items: list[dict[str, Any]] = []
    total = Decimal("0")
    for item in cart.items:
        product = db.session.get(Product, item.product_id)
        lock = pricelock.lock_for_cart_item(item.id)
        if lock is not None:
            unit_price = lock.locked_price
        else:
            # Lock expired → fall back to the supplier's current live EFFECTIVE
            # price (honouring an active discount).
            offer = db.session.get(SupplierOffer, item.supplier_offer_id)
            unit_price = offers_svc.effective_price(offer) if offer else Decimal("0")
        line_total = to_money(item.qty) * to_money(unit_price)
        total += line_total
        items.append(
            {
                "item_id": item.id,
                "product_id": item.product_id,
                "name_ar": product.name_ar if product else None,
                "qty": str(item.qty),
                "locked_unit_price": str(unit_price),
                "line_total": str(line_total),
                "price_locked_until": lock.expires_at.isoformat() if lock else None,
                # no supplier_id / supplier_offer exposure
            }
        )
    return {"cart_id": cart.id, "status": cart.status, "items": items, "total": str(total)}

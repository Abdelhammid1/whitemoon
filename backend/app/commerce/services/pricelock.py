"""Price-lock on reserved quantity (US-1.6).

When an item enters a cart, the offer's current price is locked for the
reserved quantity until the hold expires or the order is placed. A supplier
may *lower* a locked price (and we lower the live locks too, to the
customer's benefit) but may never *raise* it while a lock is live.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from ...common.errors import Conflict
from ...common.money import to_money
from ...extensions import db
from ..models import PriceLock

# Default hold duration for a reserved cart quantity.
HOLD_MINUTES = 60


def _now() -> datetime:
    return datetime.now(UTC)


def active_locks_for_offer(offer_id: int) -> list[PriceLock]:
    stmt = select(PriceLock).where(
        PriceLock.supplier_offer_id == offer_id,
        PriceLock.released_at.is_(None),
        PriceLock.consumed_at.is_(None),
        PriceLock.expires_at > _now(),
    )
    return list(db.session.execute(stmt).scalars().all())


def create_lock(
    *, offer_id: int, cart_item_id: int, qty: Decimal, price: Decimal
) -> PriceLock:
    lock = PriceLock(
        supplier_offer_id=offer_id,
        cart_item_id=cart_item_id,
        locked_qty=to_money(qty),
        locked_price=to_money(price),
        expires_at=_now() + timedelta(minutes=HOLD_MINUTES),
    )
    db.session.add(lock)
    db.session.flush()
    return lock


def lock_for_cart_item(cart_item_id: int) -> PriceLock | None:
    stmt = select(PriceLock).where(
        PriceLock.cart_item_id == cart_item_id,
        PriceLock.released_at.is_(None),
        PriceLock.consumed_at.is_(None),
    )
    return db.session.execute(stmt).scalar_one_or_none()


def release_lock_for_cart_item(cart_item_id: int) -> None:
    lock = lock_for_cart_item(cart_item_id)
    if lock is not None:
        lock.released_at = _now()
        db.session.flush()


def consume_lock_for_cart_item(cart_item_id: int) -> None:
    lock = lock_for_cart_item(cart_item_id)
    if lock is not None:
        lock.consumed_at = _now()
        db.session.flush()


def enforce_price_change(*, offer_id: int, current_price: Decimal, new_price: Decimal) -> None:
    """Called when a supplier updates an offer price.

    - Raising the price while any lock is live is rejected (US-1.6).
    - Lowering is always allowed; live locks are lowered to the new price.
    """
    current = to_money(current_price)
    new = to_money(new_price)
    if new == current:
        return
    locks = active_locks_for_offer(offer_id)
    if not locks:
        return
    if new > current:
        raise Conflict(
            "لا يمكن رفع السعر على كمية محجوزة بطلب غير مؤكد حتى انتهاء مهلة الحجز",
            code="price_locked",
        )
    # Lowering — pass the benefit to the held carts.
    for lock in locks:
        lock.locked_price = new
    db.session.flush()

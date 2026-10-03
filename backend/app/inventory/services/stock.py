"""Per-supplier, per-location stock balances (US-4.1)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select

from ...common.errors import BadRequest, NotFound
from ...common.money import to_money
from ...extensions import db
from ..models import LOCATION_TYPES, StockBalance


def get_balance(
    *, supplier_id: int, product_id: int, location_type: str, location_id: int | None
) -> StockBalance | None:
    stmt = select(StockBalance).where(
        StockBalance.supplier_id == supplier_id,
        StockBalance.product_id == product_id,
        StockBalance.location_type == location_type,
        StockBalance.location_id.is_(None)
        if location_id is None
        else StockBalance.location_id == location_id,
    )
    return db.session.execute(stmt).scalar_one_or_none()


def get_or_create_balance(
    *, supplier_id: int, product_id: int, location_type: str, location_id: int | None
) -> StockBalance:
    if location_type not in LOCATION_TYPES:
        raise BadRequest(f"location_type must be one of {LOCATION_TYPES}", code="bad_location")
    bal = get_balance(
        supplier_id=supplier_id,
        product_id=product_id,
        location_type=location_type,
        location_id=location_id,
    )
    if bal is None:
        bal = StockBalance(
            supplier_id=supplier_id,
            product_id=product_id,
            location_type=location_type,
            location_id=location_id,
            on_hand=Decimal("0"),
            reserved=Decimal("0"),
        )
        db.session.add(bal)
        db.session.flush()
    return bal


def adjust(
    *,
    supplier_id: int,
    product_id: int,
    location_type: str,
    location_id: int | None,
    delta: Decimal,
    reorder_point: Decimal | None = None,
) -> StockBalance:
    """Add `delta` (can be negative) to on_hand. Guards against negative stock
    and against dropping below reserved (DB CHECKs also enforce this)."""
    bal = get_or_create_balance(
        supplier_id=supplier_id,
        product_id=product_id,
        location_type=location_type,
        location_id=location_id,
    )
    new_on_hand = to_money(bal.on_hand) + to_money(delta)
    if new_on_hand < 0:
        raise BadRequest(
            f"insufficient stock: have {bal.on_hand}, delta {delta}",
            code="insufficient_stock",
        )
    if new_on_hand < to_money(bal.reserved):
        raise BadRequest(
            "on_hand would drop below reserved", code="below_reserved"
        )
    bal.on_hand = new_on_hand
    if reorder_point is not None:
        bal.reorder_point = to_money(reorder_point)
    db.session.flush()
    return bal


def manual_adjust(
    *,
    supplier_id: int,
    product_id: int,
    location_type: str,
    location_id: int | None,
    delta: Decimal,
    reorder_point: Decimal | None = None,
) -> StockBalance:
    bal = adjust(
        supplier_id=supplier_id,
        product_id=product_id,
        location_type=location_type,
        location_id=location_id,
        delta=delta,
        reorder_point=reorder_point,
    )
    db.session.commit()
    return bal


def list_balances(
    *, supplier_id: int | None = None, location_type: str | None = None, limit: int = 200
) -> list[StockBalance]:
    stmt = select(StockBalance).order_by(StockBalance.id.desc()).limit(limit)
    if supplier_id is not None:
        stmt = stmt.where(StockBalance.supplier_id == supplier_id)
    if location_type:
        stmt = stmt.where(StockBalance.location_type == location_type)
    return list(db.session.execute(stmt).scalars().all())


def require_available(
    *, supplier_id: int, product_id: int, location_type: str, location_id: int | None,
    qty: Decimal,
) -> StockBalance:
    bal = get_balance(
        supplier_id=supplier_id,
        product_id=product_id,
        location_type=location_type,
        location_id=location_id,
    )
    if bal is None:
        raise NotFound("No stock at source location", code="no_source_stock")
    available = to_money(bal.on_hand) - to_money(bal.reserved)
    if available < to_money(qty):
        raise BadRequest(
            f"insufficient available: {available} < {qty}",
            code="insufficient_available",
        )
    return bal


def serialize(bal: StockBalance) -> dict[str, Any]:
    on_hand = to_money(bal.on_hand)
    reserved = to_money(bal.reserved)
    reorder = bal.reorder_point
    low = reorder is not None and on_hand <= to_money(reorder)
    return {
        "id": bal.id,
        "supplier_id": bal.supplier_id,
        "product_id": bal.product_id,
        "location_type": bal.location_type,
        "location_id": bal.location_id,
        "on_hand": str(on_hand),
        "reserved": str(reserved),
        "available": str(on_hand - reserved),
        "reorder_point": str(reorder) if reorder is not None else None,
        "low": low,
    }

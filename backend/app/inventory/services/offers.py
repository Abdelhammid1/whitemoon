"""Supplier offers + server-side best-price (US-1.1, US-4.1).

Supplier-isolation rules:
- A supplier manages only their own offers (ownership checked at the route).
- `best_offer` returns the lowest active price WITHOUT the supplier id, so
  no customer-facing path can learn who the supplier is.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select

from ...common.errors import NotFound
from ...common.money import to_money
from ...extensions import db
from ..models import Product, SupplierOffer


def upsert_offer(
    *,
    supplier_id: int,
    product_id: int,
    unit_price: Decimal,
    moq: Decimal = Decimal("0"),
    is_active: bool = True,
) -> SupplierOffer:
    product = db.session.get(Product, product_id)
    if product is None:
        raise NotFound("Product not found", code="product_not_found")

    offer = db.session.execute(
        select(SupplierOffer).where(
            SupplierOffer.supplier_id == supplier_id,
            SupplierOffer.product_id == product_id,
        )
    ).scalar_one_or_none()
    if offer is None:
        offer = SupplierOffer(
            supplier_id=supplier_id,
            product_id=product_id,
            unit_price=to_money(unit_price),
            moq=to_money(moq),
            is_active=is_active,
        )
        db.session.add(offer)
    else:
        # Price-lock guard (US-1.6): a raise is rejected while any lock on
        # this offer is live; a cut is allowed and lowers the live locks.
        from ...commerce.services import pricelock

        pricelock.enforce_price_change(
            offer_id=offer.id, current_price=offer.unit_price, new_price=to_money(unit_price)
        )
        offer.unit_price = to_money(unit_price)
        offer.moq = to_money(moq)
        offer.is_active = is_active
    db.session.commit()
    return offer


def lower_price_exists(*, product_id: int, my_price: Decimal) -> bool:
    """True if any active offer on this product is cheaper than `my_price` —
    without revealing the competitor's identity or exact price (US-1.5)."""
    cheaper = db.session.execute(
        select(SupplierOffer.id)
        .where(
            SupplierOffer.product_id == product_id,
            SupplierOffer.is_active.is_(True),
            SupplierOffer.unit_price < to_money(my_price),
        )
        .limit(1)
    ).first()
    return cheaper is not None


def list_offers_for_supplier(supplier_id: int) -> list[SupplierOffer]:
    stmt = (
        select(SupplierOffer)
        .where(SupplierOffer.supplier_id == supplier_id)
        .order_by(SupplierOffer.id.desc())
    )
    return list(db.session.execute(stmt).scalars().all())


def best_offer(product_id: int) -> dict[str, Any] | None:
    """Lowest active offer for a product. NEVER returns supplier identity."""
    stmt = (
        select(SupplierOffer.unit_price, SupplierOffer.moq)
        .where(
            SupplierOffer.product_id == product_id,
            SupplierOffer.is_active.is_(True),
        )
        .order_by(SupplierOffer.unit_price.asc())
        .limit(1)
    )
    row = db.session.execute(stmt).one_or_none()
    if row is None:
        return None
    return {"best_price": str(to_money(row.unit_price)), "moq": str(to_money(row.moq))}


def serialize_own(offer: SupplierOffer) -> dict[str, Any]:
    """Full detail — only ever returned to the owning supplier or an admin.

    Includes the `lower_price_exists` hint (US-1.5): a bare signal that a
    cheaper competing offer exists, with no competitor identity or price.
    """
    return {
        "id": offer.id,
        "product_id": offer.product_id,
        "unit_price": str(offer.unit_price),
        "moq": str(offer.moq),
        "is_active": offer.is_active,
        "currency": offer.currency,
        "lower_price_exists": lower_price_exists(
            product_id=offer.product_id, my_price=offer.unit_price
        ),
    }

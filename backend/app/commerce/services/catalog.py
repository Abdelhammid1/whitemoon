"""Customer-facing catalogue browse (US-1.1).

Returns products with the best available price and NEVER a supplier id.
Aggregation (best price, lowest active offer) is computed server-side; the
supplier behind the price is not exposed in any field.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ...extensions import db
from ...inventory.models import Product, SupplierOffer


def _best_offer_subq():
    """Lowest active offer per product — carries its opaque offer id and price.
    The id lets a customer add to cart without ever seeing the supplier."""
    return (
        select(
            SupplierOffer.product_id.label("pid"),
            SupplierOffer.id.label("offer_id"),
            SupplierOffer.unit_price.label("best_price"),
        )
        .where(SupplierOffer.is_active.is_(True))
        .distinct(SupplierOffer.product_id)
        .order_by(SupplierOffer.product_id, SupplierOffer.unit_price.asc(), SupplierOffer.id.asc())
        .subquery()
    )


def browse(*, q: str | None = None, category: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    best = _best_offer_subq()
    stmt = (
        select(Product, best.c.best_price, best.c.offer_id)
        .join(best, best.c.pid == Product.id)
        .where(Product.is_active.is_(True))
        .order_by(Product.id.desc())
        .limit(limit)
    )
    if category:
        stmt = stmt.where(Product.category == category)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(Product.name_ar.ilike(pattern) | Product.sku.ilike(pattern))

    rows = db.session.execute(stmt).all()
    return [
        {
            "product_id": product.id,
            "sku": product.sku,
            "name_ar": product.name_ar,
            "category": product.category,
            "unit": product.unit,
            "image_url": product.image_url,
            "best_price": str(best_price),
            "best_offer_id": offer_id,  # opaque — no supplier revealed
        }
        for (product, best_price, offer_id) in rows
    ]


def related_products(product_id: int, *, limit: int = 8) -> list[dict[str, Any]]:
    """Cross-sell suggestions (US-4.5, T-03): other active products in the same
    category, with a best price and no supplier identity."""
    product = db.session.get(Product, product_id)
    if product is None:
        return []
    best = _best_offer_subq()
    stmt = (
        select(Product, best.c.best_price, best.c.offer_id)
        .join(best, best.c.pid == Product.id)
        .where(
            Product.is_active.is_(True),
            Product.category == product.category,
            Product.id != product_id,
        )
        .order_by(Product.id.desc())
        .limit(limit)
    )
    rows = db.session.execute(stmt).all()
    return [
        {
            "product_id": p.id,
            "sku": p.sku,
            "name_ar": p.name_ar,
            "category": p.category,
            "best_price": str(bp),
            "best_offer_id": offer_id,
        }
        for (p, bp, offer_id) in rows
    ]

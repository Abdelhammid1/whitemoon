"""Customer-facing catalogue browse (US-1.1).

Returns products with the best available price and NEVER a supplier id.
Aggregation (best price, lowest active offer) is computed server-side; the
supplier behind the price is not exposed in any field.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from ...extensions import db
from ...inventory.models import Product, SupplierOffer


def browse(*, q: str | None = None, category: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    # Best (lowest) active price per product.
    best = (
        select(
            SupplierOffer.product_id.label("pid"),
            func.min(SupplierOffer.unit_price).label("best_price"),
        )
        .where(SupplierOffer.is_active.is_(True))
        .group_by(SupplierOffer.product_id)
        .subquery()
    )
    stmt = (
        select(Product, best.c.best_price)
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
            "best_price": str(best_price),
            # deliberately no supplier_id / supplier_name
        }
        for (product, best_price) in rows
    ]

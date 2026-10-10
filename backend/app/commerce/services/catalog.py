"""Customer-facing catalogue browse (US-1.1).

Returns products with the best available price and NEVER a supplier id.
Aggregation (best price, lowest active offer) is computed server-side; the
supplier behind the price is not exposed in any field.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import and_, case, func, or_, select

from ...extensions import db
from ...inventory.models import Product, SupplierOffer


def _effective_price_expr():
    """SQL expression for an offer's price today, honouring an active discount
    (T-30): the discounted price while the discount window is open, else the
    unit price. Rounded to 4 dp to match the money convention."""
    today = date.today()
    active = and_(
        SupplierOffer.discount_kind != "none",
        SupplierOffer.discount_value.isnot(None),
        or_(SupplierOffer.discount_start.is_(None), SupplierOffer.discount_start <= today),
        or_(SupplierOffer.discount_end.is_(None), SupplierOffer.discount_end >= today),
    )
    raw = case(
        (
            and_(active, SupplierOffer.discount_kind == "percent"),
            SupplierOffer.unit_price * (1 - SupplierOffer.discount_value / 100),
        ),
        (and_(active, SupplierOffer.discount_kind == "price"), SupplierOffer.discount_value),
        else_=SupplierOffer.unit_price,
    )
    return func.round(raw, 4)


def _best_offer_subq():
    """Lowest active EFFECTIVE price per product — carries its opaque offer id
    and price. The id lets a customer add to cart without ever seeing the
    supplier. A promotional discount (T-30) lowers the effective price here."""
    eff = _effective_price_expr()
    return (
        select(
            SupplierOffer.product_id.label("pid"),
            SupplierOffer.id.label("offer_id"),
            eff.label("best_price"),
        )
        .where(SupplierOffer.is_active.is_(True))
        .distinct(SupplierOffer.product_id)
        .order_by(SupplierOffer.product_id, eff.asc(), SupplierOffer.id.asc())
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


def get_product(product_id: int) -> dict[str, Any] | None:
    """One product for the customer detail page (M2) — rich fields + best
    price, never a supplier. Returns None when the product is inactive or has
    no active offer (nothing the customer can buy)."""
    best = _best_offer_subq()
    row = db.session.execute(
        select(Product, best.c.best_price, best.c.offer_id)
        .join(best, best.c.pid == Product.id)
        .where(Product.id == product_id, Product.is_active.is_(True))
    ).first()
    if row is None:
        return None
    product, best_price, offer_id = row
    return {
        "product_id": product.id,
        "sku": product.sku,
        "name_ar": product.name_ar,
        "category": product.category,
        "subcategory": product.subcategory,
        "brand": product.brand,
        "description": product.description,
        "unit": product.unit,
        "image_url": product.image_url,
        "best_price": str(best_price),
        "best_offer_id": offer_id,  # opaque — no supplier revealed
    }


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

"""Customer-facing catalogue browse (US-1.1).

Returns products with the best available price and NEVER a supplier id.
Aggregation (best price, lowest active offer) is computed server-side; the
supplier behind the price is not exposed in any field.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from decimal import Decimal

from sqlalchemy import and_, case, func, or_, select

from ...extensions import db
from ...inventory.models import Category, Product, StockBalance, SupplierOffer


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
            SupplierOffer.supplier_id.label("supplier_id"),  # internal join only, never returned
            SupplierOffer.moq.label("moq"),
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


# ---------------------------------------------------------------- T-43 quick order

# Trigram threshold for typo-tolerant name matching (pg_trgm). Deliberately
# below the 0.3 default so a one/two-letter slip still matches.
_SIM_THRESHOLD = 0.15


def quick_search(
    *,
    q: str | None = None,
    category: str | None = None,
    brand: str | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    in_stock_only: bool = False,
    sort: str = "relevance",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Typo-tolerant search for the «طلب سريع» screen (T-43): match by name
    (fuzzy), barcode, or code (sku); filter by category/brand/price/availability;
    sort; and carry the opaque best offer + unit + available qty so a bulk buyer
    can add straight to the cart. No supplier identity is ever returned."""
    best = _best_offer_subq()
    # Available at the (opaque) best-offer supplier — a number, not an identity.
    available = func.coalesce(StockBalance.on_hand - StockBalance.reserved, 0)
    stmt = (
        select(Product, best.c.best_price, best.c.offer_id, best.c.moq, available.label("available"))
        .join(best, best.c.pid == Product.id)
        .outerjoin(
            StockBalance,
            and_(
                StockBalance.supplier_id == best.c.supplier_id,
                StockBalance.product_id == Product.id,
                StockBalance.location_type == "supplier",
                StockBalance.location_id.is_(None),
            ),
        )
        .where(Product.is_active.is_(True))
    )
    if category:
        stmt = stmt.where(Product.category == category)
    if brand:
        stmt = stmt.where(Product.brand == brand)
    if price_min is not None:
        stmt = stmt.where(best.c.best_price >= price_min)
    if price_max is not None:
        stmt = stmt.where(best.c.best_price <= price_max)
    if in_stock_only:
        stmt = stmt.where(available > 0)

    sim = None
    boost = None
    if q:
        qn = q.strip()
        sim = func.similarity(Product.name_ar, qn)
        boost = case(
            (or_(Product.barcode == qn, func.lower(Product.sku) == qn.lower()), 1),
            else_=0,
        )
        stmt = stmt.where(
            or_(
                Product.barcode == qn,
                Product.sku.ilike(f"{qn}%"),
                Product.name_ar.ilike(f"%{qn}%"),
                sim > _SIM_THRESHOLD,
            )
        )

    if sort == "price_asc":
        stmt = stmt.order_by(best.c.best_price.asc(), Product.name_ar.asc())
    elif sort == "price_desc":
        stmt = stmt.order_by(best.c.best_price.desc(), Product.name_ar.asc())
    elif sort == "name":
        stmt = stmt.order_by(Product.name_ar.asc())
    elif q is not None and sim is not None and boost is not None:  # relevance
        stmt = stmt.order_by(boost.desc(), sim.desc(), Product.name_ar.asc())
    else:
        stmt = stmt.order_by(Product.id.desc())

    stmt = stmt.limit(min(limit, 200))
    rows = db.session.execute(stmt).all()
    return [
        {
            "product_id": p.id,
            "sku": p.sku,
            "name_ar": p.name_ar,
            "category": p.category,
            "brand": p.brand,
            "barcode": p.barcode,
            "unit": p.unit,
            "image_url": p.image_url,
            "best_price": str(bp),
            "best_offer_id": offer_id,
            "moq": str(moq),
            "available": str(avail),
        }
        for (p, bp, offer_id, moq, avail) in rows
    ]


def filter_options() -> dict[str, Any]:
    """Distinct categories + brands among orderable products — populates the
    «طلب سريع» filters."""
    best = _best_offer_subq()
    brands = db.session.execute(
        select(Product.brand)
        .join(best, best.c.pid == Product.id)
        .where(Product.is_active.is_(True), Product.brand.isnot(None), Product.brand != "")
        .distinct()
        .order_by(Product.brand)
    ).scalars().all()
    cats = db.session.execute(
        select(Category.code, Category.name_ar)
        .where(Category.is_active.is_(True))
        .order_by(Category.sort_order, Category.name_ar)
    ).all()
    return {
        "brands": [b for b in brands if b],
        "categories": [{"code": c, "name_ar": n} for (c, n) in cats],
    }

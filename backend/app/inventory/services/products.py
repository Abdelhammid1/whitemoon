"""Product catalog — supplier-agnostic, admin-curated (US-4.1)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ...common.errors import Conflict, NotFound
from ...extensions import db
from ..models import CATEGORIES, Product


def create_product(
    *,
    sku: str,
    name_ar: str,
    category: str,
    unit: str = "piece",
    name_en: str | None = None,
    eta_code: str | None = None,
    food_expiry_tracked: bool = False,
    created_by: int | None = None,
) -> Product:
    if category not in CATEGORIES:
        raise Conflict(f"category must be one of {CATEGORIES}", code="bad_category")
    existing = db.session.execute(
        select(Product).where(Product.sku == sku)
    ).scalar_one_or_none()
    if existing is not None:
        raise Conflict("SKU already exists", code="sku_exists")
    product = Product(
        sku=sku,
        name_ar=name_ar,
        name_en=name_en,
        category=category,
        unit=unit,
        eta_code=eta_code,
        food_expiry_tracked=food_expiry_tracked,
        created_by=created_by,
    )
    db.session.add(product)
    db.session.commit()
    return product


def get_product(product_id: int) -> Product:
    product = db.session.get(Product, product_id)
    if product is None:
        raise NotFound("Product not found", code="product_not_found")
    return product


def list_products(
    *, q: str | None = None, category: str | None = None, limit: int = 100
) -> list[Product]:
    stmt = select(Product).order_by(Product.id.desc()).limit(limit)
    if category:
        stmt = stmt.where(Product.category == category)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(Product.sku.ilike(pattern) | Product.name_ar.ilike(pattern))
    return list(db.session.execute(stmt).scalars().all())


def serialize(product: Product) -> dict[str, Any]:
    return {
        "id": product.id,
        "sku": product.sku,
        "name_ar": product.name_ar,
        "name_en": product.name_en,
        "category": product.category,
        "unit": product.unit,
        "eta_code": product.eta_code,
        "food_expiry_tracked": product.food_expiry_tracked,
        "is_active": product.is_active,
    }

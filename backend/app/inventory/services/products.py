"""Product catalog — supplier-agnostic, admin-curated (US-4.1)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ...common.errors import Conflict, NotFound
from ...extensions import db
from ..models import Product, ProductVariant
from . import categories as categories_svc


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
    subcategory: str | None = None,
    brand: str | None = None,
    barcode: str | None = None,
    description: str | None = None,
    image_url: str | None = None,
) -> Product:
    categories_svc.assert_assignable(category)
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
        subcategory=subcategory,
        brand=brand,
        barcode=barcode,
        description=description,
        image_url=image_url,
    )
    db.session.add(product)
    db.session.commit()
    return product


def add_variant(
    *, product_id: int, sku: str, barcode: str | None, size: str | None, color: str | None
) -> ProductVariant:
    if db.session.get(Product, product_id) is None:
        raise NotFound("Product not found", code="product_not_found")
    if db.session.execute(
        select(ProductVariant).where(ProductVariant.sku == sku)
    ).scalar_one_or_none():
        raise Conflict("Variant SKU already exists", code="variant_sku_exists")
    v = ProductVariant(product_id=product_id, sku=sku, barcode=barcode, size=size, color=color)
    db.session.add(v)
    db.session.commit()
    return v


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
        "subcategory": product.subcategory,
        "brand": product.brand,
        "barcode": product.barcode,
        "description": product.description,
        "image_url": product.image_url,
        "unit": product.unit,
        "eta_code": product.eta_code,
        "food_expiry_tracked": product.food_expiry_tracked,
        "is_active": product.is_active,
        "variants": [
            {
                "id": v.id,
                "sku": v.sku,
                "barcode": v.barcode,
                "size": v.size,
                "color": v.color,
                "is_active": v.is_active,
            }
            for v in product.variants
        ],
    }

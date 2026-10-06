"""Product catalog — supplier-agnostic, admin-curated (US-4.1, T-14)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from ...common.errors import Conflict, NotFound
from ...extensions import db
from ..models import Batch, Product, ProductImage, ProductVariant
from . import categories as categories_svc

_STATUSES = ("active", "draft", "suspended")
_MAX_IMAGES = 5


def _dec(v: Any) -> Decimal | None:
    if v is None or v == "":
        return None
    return Decimal(str(v))


def _sync_primary(product: Product) -> None:
    """Keep Product.image_url pointed at the primary gallery image (or the
    first one) so the catalog shows a picture."""
    imgs = list(product.images)
    if not imgs:
        # No gallery: leave image_url untouched (legacy products set it directly).
        return
    primary = next((i for i in imgs if i.is_primary), None) or imgs[0]
    for i in imgs:
        i.is_primary = i.id == primary.id if primary.id else i is primary
    product.image_url = primary.url


def _check_unique_variant_skus(skus: list[str], *, exclude_product_id: int | None = None) -> None:
    dup = next((s for s in skus if skus.count(s) > 1), None)
    if dup is not None:
        raise Conflict(f"duplicate variant SKU {dup} in payload", code="variant_sku_dup")
    for sku in skus:
        row = db.session.execute(
            select(ProductVariant).where(ProductVariant.sku == sku)
        ).scalar_one_or_none()
        if row is not None and row.product_id != exclude_product_id:
            raise Conflict(f"variant SKU {sku} already exists", code="variant_sku_exists")


def create_product(
    *,
    sku: str,
    name_ar: str,
    category: str,
    unit: str = "piece",
    name_en: str | None = None,
    eta_code: str | None = None,
    eta_code_type: str | None = None,
    eta_ready: bool = False,
    tax_rate: Any = None,
    food_expiry_tracked: bool = False,
    created_by: int | None = None,
    subcategory: str | None = None,
    brand: str | None = None,
    barcode: str | None = None,
    description: str | None = None,
    image_url: str | None = None,
    status: str = "active",
    wholesale_price: Any = None,
    deferred_price: Any = None,
    default_moq: Any = None,
    variants: list[dict[str, Any]] | None = None,
    images: list[dict[str, Any]] | None = None,
    initial_batch: dict[str, Any] | None = None,
) -> Product:
    categories_svc.assert_assignable(category)
    if status not in _STATUSES:
        raise Conflict(f"status must be one of {_STATUSES}", code="bad_status")
    if db.session.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none():
        raise Conflict("SKU already exists", code="sku_exists")

    variants = variants or []
    images = images or []
    if len(images) > _MAX_IMAGES:
        raise Conflict(f"at most {_MAX_IMAGES} images", code="too_many_images")
    _check_unique_variant_skus([v["sku"] for v in variants if v.get("sku")])

    product = Product(
        sku=sku,
        name_ar=name_ar,
        name_en=name_en,
        category=category,
        unit=unit,
        eta_code=eta_code,
        eta_code_type=eta_code_type,
        eta_ready=eta_ready,
        tax_rate=_dec(tax_rate),
        food_expiry_tracked=food_expiry_tracked,
        created_by=created_by,
        subcategory=subcategory,
        brand=brand,
        barcode=barcode,
        description=description,
        image_url=image_url,
        status=status,
        is_active=(status == "active"),
        wholesale_price=_dec(wholesale_price),
        deferred_price=_dec(deferred_price),
        default_moq=_dec(default_moq),
    )
    for i, v in enumerate(variants):
        product.variants.append(
            ProductVariant(
                sku=v["sku"], barcode=v.get("barcode"), size=v.get("size"),
                color=v.get("color"), pack=v.get("pack"),
            )
        )
    for i, img in enumerate(images):
        product.images.append(
            ProductImage(url=img["url"], is_primary=bool(img.get("is_primary")), sort_order=i)
        )
    db.session.add(product)
    db.session.flush()
    _sync_primary(product)

    if initial_batch:
        _add_batch(product.id, initial_batch)

    db.session.commit()
    return product


def _add_batch(product_id: int, b: dict[str, Any]) -> None:
    if not b.get("supplier_id") or not b.get("batch_code"):
        raise Conflict("batch needs supplier_id and batch_code", code="bad_batch")
    db.session.add(
        Batch(
            product_id=product_id,
            supplier_id=int(b["supplier_id"]),
            batch_code=str(b["batch_code"]),
            production_date=_as_date(b.get("production_date")),
            expiry_date=_as_date(b.get("expiry_date")),
            qty_on_hand=_dec(b.get("qty")) or Decimal("0"),
        )
    )


def _as_date(v: Any) -> date | None:
    if not v:
        return None
    return date.fromisoformat(str(v)[:10])


def update_product(product_id: int, **fields: Any) -> Product:
    product = get_product(product_id)
    if "category" in fields and fields["category"]:
        categories_svc.assert_assignable(fields["category"])
    if "status" in fields and fields["status"] is not None:
        if fields["status"] not in _STATUSES:
            raise Conflict(f"status must be one of {_STATUSES}", code="bad_status")

    simple = (
        "name_ar", "name_en", "category", "unit", "eta_code", "eta_code_type",
        "subcategory", "brand", "barcode", "description",
    )
    for key in simple:
        if key in fields and fields[key] is not None:
            setattr(product, key, fields[key])
    for key in ("wholesale_price", "deferred_price", "default_moq", "tax_rate"):
        if key in fields:
            setattr(product, key, _dec(fields[key]))
    for key in ("eta_ready", "food_expiry_tracked"):
        if key in fields and fields[key] is not None:
            setattr(product, key, bool(fields[key]))
    if fields.get("status"):
        product.status = str(fields["status"])
        product.is_active = fields["status"] == "active"

    # Replace variants / images wholesale when provided.
    if fields.get("variants") is not None:
        _check_unique_variant_skus(
            [v["sku"] for v in fields["variants"] if v.get("sku")], exclude_product_id=product_id
        )
        product.variants.clear()
        db.session.flush()  # emit the orphan DELETEs before re-INSERTing same SKUs
        for v in fields["variants"]:
            product.variants.append(
                ProductVariant(
                    sku=v["sku"], barcode=v.get("barcode"), size=v.get("size"),
                    color=v.get("color"), pack=v.get("pack"),
                )
            )
    if fields.get("images") is not None:
        imgs = fields["images"]
        if len(imgs) > _MAX_IMAGES:
            raise Conflict(f"at most {_MAX_IMAGES} images", code="too_many_images")
        product.images.clear()
        db.session.flush()
        for i, img in enumerate(imgs):
            product.images.append(
                ProductImage(url=img["url"], is_primary=bool(img.get("is_primary")), sort_order=i)
            )
    db.session.flush()
    _sync_primary(product)
    db.session.commit()
    return product


def add_variant(
    *, product_id: int, sku: str, barcode: str | None, size: str | None,
    color: str | None, pack: str | None = None,
) -> ProductVariant:
    if db.session.get(Product, product_id) is None:
        raise NotFound("Product not found", code="product_not_found")
    _check_unique_variant_skus([sku])
    v = ProductVariant(product_id=product_id, sku=sku, barcode=barcode, size=size, color=color, pack=pack)
    db.session.add(v)
    db.session.commit()
    return v


def add_image(
    product_id: int, *, url: str | None = None, storage_key: str | None = None,
    is_primary: bool = False,
) -> ProductImage:
    """Attach an image: either an external `url`, or an uploaded file via
    `storage_key` (then url is the serve route)."""
    product = get_product(product_id)
    if len(product.images) >= _MAX_IMAGES:
        raise Conflict(f"at most {_MAX_IMAGES} images", code="too_many_images")
    want_primary = is_primary or not product.images
    img = ProductImage(
        product_id=product_id, url=url or "", storage_key=storage_key,
        is_primary=want_primary, sort_order=len(product.images),
    )
    product.images.append(img)
    db.session.flush()
    if storage_key and not url:
        img.url = f"/inventory/product-images/{img.id}"
    if want_primary:
        # An explicit primary wins over any existing one (ordering-independent).
        for other in product.images:
            other.is_primary = other.id == img.id
        product.image_url = img.url
    else:
        _sync_primary(product)
    db.session.commit()
    return img


def delete_image(product_id: int, image_id: int) -> None:
    product = get_product(product_id)
    img = next((i for i in product.images if i.id == image_id), None)
    if img is None:
        raise NotFound("image not found", code="image_not_found")
    product.images.remove(img)
    db.session.flush()
    _sync_primary(product)
    db.session.commit()


def set_primary_image(product_id: int, image_id: int) -> None:
    product = get_product(product_id)
    target = next((i for i in product.images if i.id == image_id), None)
    if target is None:
        raise NotFound("image not found", code="image_not_found")
    for i in product.images:
        i.is_primary = i.id == image_id
    product.image_url = target.url
    db.session.commit()


def get_product(product_id: int) -> Product:
    product = db.session.get(Product, product_id)
    if product is None:
        raise NotFound("Product not found", code="product_not_found")
    return product


def list_products(
    *, q: str | None = None, category: str | None = None, status: str | None = None, limit: int = 100
) -> list[Product]:
    stmt = select(Product).order_by(Product.id.desc()).limit(limit)
    if category:
        stmt = stmt.where(Product.category == category)
    if status:
        stmt = stmt.where(Product.status == status)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(Product.sku.ilike(pattern) | Product.name_ar.ilike(pattern))
    return list(db.session.execute(stmt).scalars().all())


def serialize(product: Product) -> dict[str, Any]:
    def _s(v: Decimal | None) -> str | None:
        return str(v) if v is not None else None

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
        "eta_code_type": product.eta_code_type,
        "eta_ready": product.eta_ready,
        "tax_rate": _s(product.tax_rate),
        "food_expiry_tracked": product.food_expiry_tracked,
        "status": product.status,
        "is_active": product.is_active,
        "wholesale_price": _s(product.wholesale_price),
        "deferred_price": _s(product.deferred_price),
        "default_moq": _s(product.default_moq),
        "variants": [
            {
                "id": v.id, "sku": v.sku, "barcode": v.barcode, "size": v.size,
                "color": v.color, "pack": v.pack, "is_active": v.is_active,
            }
            for v in product.variants
        ],
        "images": [
            {"id": im.id, "url": im.url, "is_primary": im.is_primary, "sort_order": im.sort_order}
            for im in product.images
        ],
    }

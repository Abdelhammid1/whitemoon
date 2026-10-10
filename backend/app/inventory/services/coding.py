"""Supplier product-coding requests (T-30).

A supplier asks for a new item to be coded into the catalog. Here we create the
request and notify the admins who manage the catalog; the full review queue and
barcode-identity resolution are T-31.
"""

from __future__ import annotations

from typing import Any

from ...common.errors import BadRequest
from ...extensions import db
from ..models import ProductCodingRequest


def create_request(
    *,
    supplier_id: int,
    name: str,
    barcode: str | None = None,
    brand: str | None = None,
    category: str | None = None,
    image_url: str | None = None,
    note: str | None = None,
) -> ProductCodingRequest:
    if not name or not name.strip():
        raise BadRequest("اسم الصنف مطلوب", code="name_required")
    row = ProductCodingRequest(
        supplier_id=supplier_id,
        name=name.strip(),
        barcode=(barcode or None),
        brand=(brand or None),
        category=(category or None),
        image_url=(image_url or None),
        note=(note or None),
        status="new",
    )
    db.session.add(row)
    db.session.commit()
    _notify_admins(row)
    return row


def _notify_admins(row: ProductCodingRequest) -> None:
    """Notify everyone who manages the catalog (product.manage). Never raises."""
    try:
        from ...identity.services.rbac import users_with_permission
        from ...notifications.services import notify as notify_svc

        for uid in users_with_permission("product.manage"):
            notify_svc.notify(
                user_id=uid,
                title="طلب تكويد صنف جديد",
                body=f"طلب مورد تكويد صنف «{row.name}» لإضافته إلى الكتالوج.",
                type_="coding_request",
                channel="in_app",
            )
    except Exception:  # pragma: no cover - the request is already saved
        pass


def serialize(row: ProductCodingRequest) -> dict[str, Any]:
    return {
        "id": row.id,
        "supplier_id": row.supplier_id,
        "name": row.name,
        "barcode": row.barcode,
        "brand": row.brand,
        "category": row.category,
        "image_url": row.image_url,
        "note": row.note,
        "status": row.status,
        "reject_reason": row.reject_reason,
        "product_id": row.product_id,
        "created_at": row.created_at.isoformat(),
    }


def list_for_supplier(supplier_id: int) -> list[ProductCodingRequest]:
    from sqlalchemy import select

    return list(
        db.session.execute(
            select(ProductCodingRequest)
            .where(ProductCodingRequest.supplier_id == supplier_id)
            .order_by(ProductCodingRequest.id.desc())
        ).scalars()
    )

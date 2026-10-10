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


# ---------------------------------------------------------------- admin queue (T-31)


def list_all(*, status: str | None = None, limit: int = 200) -> list[ProductCodingRequest]:
    from sqlalchemy import select

    stmt = select(ProductCodingRequest).order_by(ProductCodingRequest.id.desc()).limit(limit)
    if status:
        stmt = stmt.where(ProductCodingRequest.status == status)
    return list(db.session.execute(stmt).scalars())


def _get(request_id: int) -> ProductCodingRequest:
    from ...common.errors import NotFound

    row = db.session.get(ProductCodingRequest, request_id)
    if row is None:
        raise NotFound("طلب التكويد غير موجود", code="coding_request_not_found")
    return row


def _notify_supplier(row: ProductCodingRequest, *, title: str, body: str, type_: str) -> None:
    try:
        from ...notifications.services import notify as notify_svc

        notify_svc.notify(user_id=row.supplier_id, title=title, body=body, type_=type_, channel="in_app")
    except Exception:  # pragma: no cover
        pass


def mark_coded(*, request_id: int, product_id: int) -> ProductCodingRequest:
    """Link a request to the product that was created from it (T-31)."""
    from ...common.errors import Conflict

    row = _get(request_id)
    if row.status == "coded":
        raise Conflict("الطلب مُكوَّد بالفعل", code="already_coded")
    row.status = "coded"
    row.product_id = product_id
    db.session.commit()
    _notify_supplier(
        row,
        title="تم تكويد الصنف",
        body=f"أُضيف الصنف «{row.name}» إلى الكتالوج ويمكنك الآن عرضه وتسعيره.",
        type_="coding_coded",
    )
    return row


def reject(*, request_id: int, reason: str) -> ProductCodingRequest:
    from ...common.errors import BadRequest, Conflict

    if len((reason or "").strip()) < 3:
        raise BadRequest("سبب الرفض مطلوب", code="reason_required")
    row = _get(request_id)
    if row.status in ("coded", "rejected"):
        raise Conflict("لا يمكن رفض طلب مُغلق", code="not_open")
    row.status = "rejected"
    row.reject_reason = reason.strip()
    db.session.commit()
    _notify_supplier(
        row,
        title="رُفض طلب التكويد",
        body=f"لم يُقبل طلب تكويد «{row.name}». السبب: {reason.strip()}",
        type_="coding_rejected",
    )
    return row


def mark_in_review(*, request_id: int) -> ProductCodingRequest:
    row = _get(request_id)
    if row.status == "new":
        row.status = "in_review"
        db.session.commit()
    return row

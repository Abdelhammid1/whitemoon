"""/inventory blueprint — products, offers, stock, transfers, shortages, reorder."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError
from sqlalchemy import select

from ..common.errors import ApiError, BadRequest, Forbidden, NotFound, Unauthorized
from ..extensions import db
from ..identity.services.audit import emit as audit_emit
from ..identity.services.rbac import has_permission, require_permission
from .models import TransferOrder
from .schemas import (
    CodingRequestIn,
    OfferIn,
    ShortageIn,
    ShortageResolveIn,
    StockAdjustIn,
    SupplierProductIn,
    TransferOrderIn,
    VariantIn,
)
from .services import categories as categories_svc
from .services import coding as coding_svc
from .services import offers as offers_svc
from .services import products as products_svc

# Product-image upload hardening (T-14): only real raster images.
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_IMAGE_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif",
}


def _is_raster_image(data: bytes) -> bool:
    """Signature sniff — rejects SVG/HTML/scripts regardless of extension."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:3] == b"\xff\xd8\xff":  # JPEG
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False
from .services import reorder as reorder_svc
from .services import shortages as shortages_svc
from .services import stock as stock_svc
from .services import transfers as transfers_svc
from .services.transfers import LineInput

bp = Blueprint("inventory", __name__, url_prefix="/inventory")


def _parse(model_cls: Any) -> Any:
    try:
        return model_cls.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        raise BadRequest(
            f"Invalid payload: {e.errors()[0]['msg']}", code="validation_error"
        ) from e


def _uid() -> int:
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    return int(raw)


# ================================================================ products


@bp.post("/products")
@require_permission("product.manage")
def create_product():
    body: Any = request.get_json(silent=True) or {}
    # sku is OPTIONAL (T-31): a global barcode is the identity, and a local
    # product with no barcode gets an auto WM-NNNNNN internal code.
    for req in ("name_ar", "category"):
        if not str(body.get(req) or "").strip():
            raise BadRequest(f"{req} is required", code="validation_error")
    product = products_svc.create_product(
        sku=(str(body.get("sku")).strip() if body.get("sku") else None),
        name_ar=body["name_ar"], category=body["category"],
        unit=body.get("unit") or "piece", name_en=body.get("name_en"),
        eta_code=body.get("eta_code"), eta_code_type=body.get("eta_code_type"),
        eta_ready=bool(body.get("eta_ready")), tax_rate=body.get("tax_rate"),
        food_expiry_tracked=bool(body.get("food_expiry_tracked")), created_by=_uid(),
        subcategory=body.get("subcategory"), brand=body.get("brand"),
        barcode=body.get("barcode"), description=body.get("description"),
        image_url=body.get("image_url"), status=body.get("status") or "active",
        wholesale_price=body.get("wholesale_price"), deferred_price=body.get("deferred_price"),
        default_moq=body.get("default_moq"), variants=body.get("variants") or [],
        images=body.get("images") or [], initial_batch=body.get("initial_batch"),
    )
    audit_emit("inventory.product.create", actor_user_id=_uid(), target_type="product", target_id=product.id)
    # Created from a supplier's coding request → link + mark coded + notify (T-31).
    coding_request_id = body.get("coding_request_id")
    if coding_request_id:
        coding_svc.mark_coded(request_id=int(coding_request_id), product_id=product.id)
        audit_emit("inventory.coding_request.coded", actor_user_id=_uid(), target_type="coding_request", target_id=int(coding_request_id))
    return jsonify(products_svc.serialize(product)), 201


@bp.get("/products/similar")
@require_permission("product.manage")
def products_similar():
    """Possible duplicates for a new product (T-31) — warn before creating."""
    return jsonify({
        "items": products_svc.find_similar(
            name=request.args.get("name"), barcode=request.args.get("barcode")
        )
    })


@bp.put("/products/<int:product_id>")
@require_permission("product.manage")
def update_product(product_id: int):
    body: Any = request.get_json(silent=True) or {}
    # Never let a body key shadow the path id (would be a TypeError -> 500).
    body.pop("id", None)
    body.pop("product_id", None)
    product = products_svc.update_product(product_id, **body)
    audit_emit("inventory.product.update", actor_user_id=_uid(), target_type="product", target_id=product.id)
    return jsonify(products_svc.serialize(product))


@bp.get("/products/<int:product_id>")
@require_permission("product.manage")
def get_product_detail(product_id: int):
    # Admin/staff detail — exposes internal pricing/variants. Customers use the
    # supplier-blind /catalog/products/<id> instead.
    return jsonify(products_svc.serialize(products_svc.get_product(product_id)))


@bp.post("/products/<int:product_id>/variants")
@require_permission("product.manage")
def add_variant(product_id: int):
    payload = _parse(VariantIn)
    v = products_svc.add_variant(
        product_id=product_id, sku=payload.sku, barcode=payload.barcode,
        size=payload.size, color=payload.color, pack=getattr(payload, "pack", None),
    )
    audit_emit(
        "inventory.variant.create", actor_user_id=_uid(),
        target_type="product_variant", target_id=v.id,
    )
    return jsonify({"id": v.id, "product_id": v.product_id, "sku": v.sku}), 201


@bp.post("/products/<int:product_id>/images")
@require_permission("product.manage")
def add_product_image(product_id: int):
    """Attach an image: a multipart file upload, or {url} JSON for an external
    image. Returns the stored image's servable URL."""
    f = request.files.get("image")
    if f is None:
        body: Any = request.get_json(silent=True) or {}
        if not body.get("url"):
            raise BadRequest("image file or url required", code="validation_error")
        img = products_svc.add_image(product_id, url=body["url"], is_primary=bool(body.get("is_primary")))
    else:
        from ..accounting.providers import storage

        data = f.read()
        # Only accept real raster images; an SVG/HTML served inline would be
        # stored XSS against the public catalog. Check extension AND magic bytes.
        name = f.filename or ""
        ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
        if ext not in _IMAGE_EXTS or not _is_raster_image(data):
            raise BadRequest("الصورة يجب أن تكون PNG أو JPG أو WEBP أو GIF", code="bad_image")
        key = storage.store(data, prefix="products", ext=ext)
        img = products_svc.add_image(
            product_id, storage_key=key, is_primary=bool(request.form.get("is_primary")),
        )
    audit_emit("inventory.product.image", actor_user_id=_uid(), target_type="product", target_id=product_id)
    return jsonify({"id": img.id, "url": img.url, "is_primary": img.is_primary}), 201


@bp.delete("/products/<int:product_id>/images/<int:image_id>")
@require_permission("product.manage")
def delete_product_image(product_id: int, image_id: int):
    products_svc.delete_image(product_id, image_id)
    audit_emit("inventory.product.image.delete", actor_user_id=_uid(), target_type="product", target_id=product_id)
    return jsonify({"deleted": image_id})


@bp.post("/products/<int:product_id>/images/<int:image_id>/primary")
@require_permission("product.manage")
def set_primary_product_image(product_id: int, image_id: int):
    products_svc.set_primary_image(product_id, image_id)
    return jsonify({"primary": image_id})


@bp.get("/product-images/<int:image_id>")
def serve_product_image(image_id: int):
    """Public: catalog/product images are not sensitive. Served with a fixed
    image MIME + hardening headers so a stored file can't execute in a browser."""
    from flask import Response

    from ..accounting.providers import storage
    from .models import ProductImage

    img = db.session.get(ProductImage, image_id)
    if img is None or not img.storage_key:
        raise NotFound("image not found", code="image_not_found")
    data = storage.load(img.storage_key)
    if data is None:
        raise NotFound("image not found", code="image_not_found")
    ext = ("." + img.storage_key.rsplit(".", 1)[-1].lower()) if "." in img.storage_key else ""
    mime = _IMAGE_MIME.get(ext, "application/octet-stream")
    resp = Response(data, mimetype=mime)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
    if mime == "application/octet-stream":  # defensive: never render unknown inline
        resp.headers["Content-Disposition"] = "attachment"
    return resp


@bp.get("/products")
@require_permission("product.manage")
def list_products():
    # Admin/staff catalog management view (internal fields). Customer browsing
    # goes through /catalog/products, which hides suppliers and internal pricing.
    items = products_svc.list_products(
        q=request.args.get("q"),
        category=request.args.get("category"),
        status=request.args.get("status"),
        limit=min(int(request.args.get("limit", "100")), 500),
    )
    return jsonify({"items": [products_svc.serialize(p) for p in items]})


@bp.get("/products/<int:product_id>/best-price")
@jwt_required()
def product_best_price(product_id: int):
    """Customer-facing: returns the best price only, never the supplier."""
    products_svc.get_product(product_id)
    best = offers_svc.best_offer(product_id)
    return jsonify({"product_id": product_id, "best": best})


# ================================================================ offers


@bp.post("/offers")
@require_permission("offer.manage")
def upsert_offer():
    payload = _parse(OfferIn)
    supplier_id = _uid()  # supplier manages only their own offers
    offer = offers_svc.upsert_offer(
        supplier_id=supplier_id,
        product_id=payload.product_id,
        unit_price=Decimal(str(payload.unit_price)),
        moq=Decimal(str(payload.moq)),
        is_active=payload.is_active,
    )
    audit_emit(
        "inventory.offer.upsert",
        actor_user_id=supplier_id,
        target_type="offer",
        target_id=offer.id,
    )
    return jsonify(offers_svc.serialize_own(offer)), 201


@bp.get("/offers/mine")
@require_permission("offer.manage")
def my_offers():
    items = offers_svc.list_offers_for_supplier(_uid())
    return jsonify({"items": [offers_svc.serialize_own(o) for o in items]})


# ================================================================ unified supplier products (T-30)


@bp.get("/supplier/products")
@require_permission("offer.manage")
def supplier_products():
    """«منتجاتي» — every product the supplier offers or stocks, with price,
    discount, moq, active and on-hand in one view."""
    return jsonify({"items": offers_svc.supplier_products(_uid())})


@bp.put("/supplier/products/<int:product_id>")
@require_permission("offer.manage")
def set_supplier_product(product_id: int):
    """Set price + discount + moq + active + quantity for the supplier's own
    product in one call. The discount is validated for platform-best price."""
    p = _parse(SupplierProductIn)
    supplier_id = _uid()
    result = offers_svc.set_supplier_product(
        supplier_id=supplier_id,
        product_id=product_id,
        unit_price=Decimal(str(p.unit_price)),
        on_hand=Decimal(str(p.on_hand)) if p.on_hand is not None else None,
        moq=Decimal(str(p.moq)),
        is_active=p.is_active,
        discount_kind=p.discount_kind,
        discount_value=Decimal(str(p.discount_value)) if p.discount_value is not None else None,
        discount_start=p.discount_start,
        discount_end=p.discount_end,
        reorder_point=Decimal(str(p.reorder_point)) if p.reorder_point is not None else None,
    )
    audit_emit(
        "inventory.supplier_product.set",
        actor_user_id=supplier_id,
        target_type="product",
        target_id=product_id,
    )
    return jsonify(result)


@bp.get("/supplier/products/template.xlsx")
@require_permission("offer.manage")
def supplier_products_template():
    """T-39: download the bulk-update Excel template."""
    from .services import bulk as bulk_svc

    return bulk_svc.xlsx_response(bulk_svc.template_bytes(), "whitemoon-products-template.xlsx")


@bp.get("/supplier/products/export.xlsx")
@require_permission("offer.manage")
def supplier_products_export():
    """T-39: export the supplier's current products in the template shape."""
    from .services import bulk as bulk_svc

    return bulk_svc.xlsx_response(bulk_svc.export_bytes(_uid()), "whitemoon-my-products.xlsx")


@bp.post("/supplier/products/bulk")
@require_permission("offer.manage")
def supplier_products_bulk():
    """T-39: validate (mode=preview) or apply (mode=apply) a bulk-update file."""
    from .services import bulk as bulk_svc

    f = request.files.get("file")
    if f is None or not f.filename:
        raise BadRequest("مطلوب ملف Excel", code="file_required")
    data = f.read(12 * 1024 * 1024 + 1)  # 12 MiB cap — ample for thousands of rows
    if not data:
        raise BadRequest("الملف فارغ", code="empty_file")
    if len(data) > 12 * 1024 * 1024:
        raise BadRequest("حجم الملف كبير جدًا", code="file_too_large")
    try:
        mode = request.args.get("mode", "preview")
        if mode == "apply":
            result = bulk_svc.apply(supplier_id=_uid(), data=data)
            audit_emit("inventory.products.bulk_apply", actor_user_id=_uid(), target_type="supplier", target_id=_uid())
            return jsonify(result)
        return jsonify(bulk_svc.preview(supplier_id=_uid(), data=data))
    except BadRequest:
        raise
    except Exception as e:
        raise BadRequest("تعذّر قراءة الملف — تأكد أنه بصيغة Excel الصحيحة", code="bad_file") from e


@bp.post("/coding-requests")
@require_permission("offer.manage")
def create_coding_request():
    p = _parse(CodingRequestIn)
    supplier_id = _uid()
    row = coding_svc.create_request(
        supplier_id=supplier_id,
        name=p.name,
        barcode=p.barcode,
        brand=p.brand,
        category=p.category,
        image_url=p.image_url,
        note=p.note,
    )
    audit_emit(
        "inventory.coding_request.created",
        actor_user_id=supplier_id,
        target_type="coding_request",
        target_id=row.id,
    )
    return jsonify(coding_svc.serialize(row)), 201


@bp.get("/coding-requests/mine")
@require_permission("offer.manage")
def my_coding_requests():
    items = coding_svc.list_for_supplier(_uid())
    return jsonify({"items": [coding_svc.serialize(r) for r in items]})


# ---- admin coding queue (T-31) ----


@bp.get("/coding-requests")
@require_permission("product.manage")
def list_coding_requests():
    items = coding_svc.list_all(status=request.args.get("status"))
    return jsonify({"items": [coding_svc.serialize(r) for r in items]})


@bp.post("/coding-requests/<int:request_id>/review")
@require_permission("product.manage")
def review_coding_request(request_id: int):
    row = coding_svc.mark_in_review(request_id=request_id)
    audit_emit("inventory.coding_request.review", actor_user_id=_uid(), target_type="coding_request", target_id=request_id)
    return jsonify(coding_svc.serialize(row))


@bp.post("/coding-requests/<int:request_id>/reject")
@require_permission("product.manage")
def reject_coding_request(request_id: int):
    body: Any = request.get_json(silent=True) or {}
    row = coding_svc.reject(request_id=request_id, reason=str(body.get("reason") or ""))
    audit_emit("inventory.coding_request.reject", actor_user_id=_uid(), target_type="coding_request", target_id=request_id, reason=row.reject_reason)
    return jsonify(coding_svc.serialize(row))


# ================================================================ stock


@bp.post("/stock/adjust")
@require_permission("inventory.manage")
def stock_adjust():
    payload = _parse(StockAdjustIn)
    bal = stock_svc.manual_adjust(
        supplier_id=payload.supplier_id,
        product_id=payload.product_id,
        location_type=payload.location_type,
        location_id=payload.location_id,
        delta=Decimal(str(payload.delta)),
        reorder_point=Decimal(str(payload.reorder_point))
        if payload.reorder_point is not None
        else None,
    )
    audit_emit(
        "inventory.stock.adjust",
        actor_user_id=_uid(),
        target_type="stock_balance",
        target_id=bal.id,
    )
    return jsonify(stock_svc.serialize(bal))


@bp.get("/stock-balances")
@jwt_required()
def stock_balances():
    # Suppliers see only their own stock; admins/staff can pass supplier_id.
    uid = _uid()
    if has_permission(uid, "inventory.manage"):
        supplier_id = request.args.get("supplier_id", type=int)
    else:
        supplier_id = uid  # supplier isolation
    items = stock_svc.list_balances(
        supplier_id=supplier_id,
        location_type=request.args.get("location_type"),
    )
    return jsonify({"items": [stock_svc.serialize(b) for b in items]})


# ================================================================ transfers


@bp.post("/transfers")
@require_permission("inventory.manage")
def create_transfer():
    payload = _parse(TransferOrderIn)
    order = transfers_svc.create_transfer_order(
        supplier_id=payload.supplier_id,
        from_location_type=payload.from_location_type,
        from_location_id=payload.from_location_id,
        to_location_type=payload.to_location_type,
        to_location_id=payload.to_location_id,
        lines=[
            LineInput(
                product_id=li.product_id,
                qty=Decimal(str(li.qty)),
                unit_cost=Decimal(str(li.unit_cost)),
            )
            for li in payload.lines
        ],
        initiated_by=_uid(),
    )
    audit_emit(
        "inventory.transfer.create",
        actor_user_id=_uid(),
        target_type="transfer_order",
        target_id=order.id,
    )
    return jsonify(transfers_svc.serialize(order)), 201


@bp.post("/transfers/<int:order_id>/issue")
@require_permission("inventory.manage")
def issue_transfer(order_id: int):
    order = transfers_svc.issue(order_id=order_id, issued_by=_uid())
    audit_emit(
        "inventory.transfer.issue",
        actor_user_id=_uid(),
        target_type="transfer_order",
        target_id=order.id,
    )
    return jsonify(transfers_svc.serialize(order))


@bp.post("/transfers/<int:order_id>/receive")
@require_permission("inventory.manage")
def receive_transfer(order_id: int):
    order = transfers_svc.receive(order_id=order_id, received_by=_uid())
    audit_emit(
        "inventory.transfer.receive",
        actor_user_id=_uid(),
        target_type="transfer_order",
        target_id=order.id,
    )
    return jsonify(transfers_svc.serialize(order))


@bp.get("/transfers")
@jwt_required()
def list_transfers():
    uid = _uid()
    stmt = select(TransferOrder).order_by(TransferOrder.id.desc()).limit(200)
    # Suppliers see only their own transfers; finance/ops see all.
    if not has_permission(uid, "inventory.manage"):
        stmt = stmt.where(TransferOrder.supplier_id == uid)
    rows = db.session.execute(stmt).scalars().all()
    return jsonify({"items": [transfers_svc.serialize(o) for o in rows]})


@bp.get("/transfers/<int:order_id>")
@jwt_required()
def get_transfer(order_id: int):
    order = db.session.get(TransferOrder, order_id)
    if order is None:
        raise BadRequest("not found", code="transfer_not_found")
    uid = _uid()
    if not has_permission(uid, "inventory.manage") and order.supplier_id != uid:
        raise Forbidden("not your transfer", code="forbidden")
    return jsonify(transfers_svc.serialize(order))


# ================================================================ shortages


@bp.post("/shortages")
@jwt_required()
def report_shortage():
    payload = _parse(ShortageIn)
    shortage = shortages_svc.report_shortage(
        reporter_user_id=_uid(),
        supplier_id=payload.supplier_id,
        product_id=payload.product_id,
        qty=Decimal(str(payload.qty)),
        unit_cost=Decimal(str(payload.unit_cost)),
        transfer_order_id=payload.transfer_order_id,
        evidence_s3_keys=payload.evidence_s3_keys,
    )
    audit_emit(
        "inventory.shortage.report",
        actor_user_id=_uid(),
        target_type="shortage",
        target_id=shortage.id,
    )
    return jsonify(shortages_svc.serialize(shortage)), 201


@bp.post("/shortages/<int:shortage_id>/resolve")
@require_permission("shortage.resolve")
def resolve_shortage(shortage_id: int):
    payload = _parse(ShortageResolveIn)
    shortage = shortages_svc.resolve_shortage(
        shortage_id=shortage_id,
        responsible_party_type=payload.responsible_party_type,
        responsible_party_id=payload.responsible_party_id,
        reason=payload.reason,
        resolved_by=_uid(),
    )
    audit_emit(
        "inventory.shortage.resolve",
        actor_user_id=_uid(),
        target_type="shortage",
        target_id=shortage.id,
        reason=payload.reason,
    )
    return jsonify(shortages_svc.serialize(shortage))


@bp.get("/shortages")
@require_permission("shortage.resolve")
def list_shortages():
    items = shortages_svc.list_shortages(status=request.args.get("status"))
    return jsonify({"items": [shortages_svc.serialize(s) for s in items]})


# ================================================================ reorder


@bp.post("/reorder/check")
@require_permission("inventory.manage")
def reorder_check():
    created = reorder_svc.check(supplier_id=request.args.get("supplier_id", type=int))
    return jsonify({"created": [reorder_svc.serialize(a) for a in created]})


@bp.get("/categories")
@jwt_required()
def list_categories():
    """Active product categories (admin-managed, T-15) — the UI's single
    source for catalog filters and the product form."""
    items = [categories_svc.serialize(c) for c in categories_svc.list_categories(active_only=True)]
    return jsonify({"items": items})


@bp.get("/categories/manage")
@require_permission("product.manage")
def list_categories_manage():
    """All categories incl. inactive, with product counts — admin page."""
    return jsonify({"items": categories_svc.list_for_management()})


@bp.post("/categories")
@require_permission("product.manage")
def create_category():
    body: Any = request.get_json(silent=True) or {}
    if not (body.get("name_ar") or "").strip():
        raise BadRequest("name_ar is required", code="validation_error")
    c = categories_svc.create(
        code=body.get("code"),
        name_ar=body["name_ar"],
        name_en=body.get("name_en"),
        icon=body.get("icon"),
        image_url=body.get("image_url"),
        parent_code=body.get("parent_code"),
        sort_order=body.get("sort_order"),
    )
    audit_emit("inventory.category.create", actor_user_id=_uid(), target_type="category", target_id=c.id)
    return jsonify(categories_svc.serialize(c)), 201


@bp.put("/categories/<code>")
@require_permission("product.manage")
def update_category(code: str):
    body: Any = request.get_json(silent=True) or {}
    c = categories_svc.update(
        code,
        name_ar=body.get("name_ar"),
        name_en=body.get("name_en"),
        icon=body.get("icon"),
        image_url=body.get("image_url"),
        parent_code=body.get("parent_code"),
        sort_order=body.get("sort_order"),
        is_active=body.get("is_active"),
    )
    audit_emit("inventory.category.update", actor_user_id=_uid(), target_type="category", target_id=c.id)
    return jsonify(categories_svc.serialize(c))


@bp.delete("/categories/<code>")
@require_permission("product.manage")
def delete_category(code: str):
    categories_svc.delete(code)
    audit_emit("inventory.category.delete", actor_user_id=_uid(), target_type="category", target_id=code)
    return jsonify({"deleted": code})


@bp.get("/location-types")
@jwt_required()
def list_location_types():
    """Stock/transfer location types (code + Arabic label) — the UI's single
    source so its picker can't drift from the CHECK constraint."""
    from .models import LOCATION_TYPE_LABELS, LOCATION_TYPES

    return jsonify(
        {"items": [{"code": t, "label": LOCATION_TYPE_LABELS.get(t, t)} for t in LOCATION_TYPES]}
    )


@bp.get("/reorder/alerts")
@require_permission("inventory.manage")
def reorder_alerts():
    open_only = request.args.get("open", "true").lower() != "false"
    alerts = reorder_svc.list_alerts(open_only=open_only)
    return jsonify({"items": [reorder_svc.serialize(a) for a in alerts]})


@bp.post("/reorder/escalate")
@require_permission("inventory.manage")
def reorder_escalate():
    """Advance the low-stock escalation chain (also run on a schedule)."""
    return jsonify(reorder_svc.escalate())


@bp.post("/reorder/alerts/<int:alert_id>/ack")
@require_permission("inventory.manage")
def reorder_ack(alert_id: int):
    alert = reorder_svc.acknowledge(alert_id=alert_id, user_id=_uid())
    return jsonify(reorder_svc.serialize(alert))


# ================================================================ errors


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

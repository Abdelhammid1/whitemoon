"""/inventory blueprint — products, offers, stock, transfers, shortages, reorder."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError
from sqlalchemy import select

from ..common.errors import ApiError, BadRequest, Forbidden, Unauthorized
from ..extensions import db
from ..identity.services.audit import emit as audit_emit
from ..identity.services.rbac import has_permission, require_permission
from .models import TransferOrder
from .schemas import (
    OfferIn,
    ProductIn,
    ShortageIn,
    ShortageResolveIn,
    StockAdjustIn,
    TransferOrderIn,
    VariantIn,
)
from .services import offers as offers_svc
from .services import products as products_svc
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
    payload = _parse(ProductIn)
    product = products_svc.create_product(
        sku=payload.sku,
        name_ar=payload.name_ar,
        name_en=payload.name_en,
        category=payload.category,
        unit=payload.unit,
        eta_code=payload.eta_code,
        food_expiry_tracked=payload.food_expiry_tracked,
        created_by=_uid(),
        subcategory=payload.subcategory,
        brand=payload.brand,
        barcode=payload.barcode,
        description=payload.description,
        image_url=payload.image_url,
    )
    audit_emit(
        "inventory.product.create",
        actor_user_id=_uid(),
        target_type="product",
        target_id=product.id,
    )
    return jsonify(products_svc.serialize(product)), 201


@bp.post("/products/<int:product_id>/variants")
@require_permission("product.manage")
def add_variant(product_id: int):
    payload = _parse(VariantIn)
    v = products_svc.add_variant(
        product_id=product_id,
        sku=payload.sku,
        barcode=payload.barcode,
        size=payload.size,
        color=payload.color,
    )
    audit_emit(
        "inventory.variant.create",
        actor_user_id=_uid(),
        target_type="product_variant",
        target_id=v.id,
    )
    return jsonify({"id": v.id, "product_id": v.product_id, "sku": v.sku}), 201


@bp.get("/products")
@jwt_required()
def list_products():
    items = products_svc.list_products(
        q=request.args.get("q"),
        category=request.args.get("category"),
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
    """Allowed product categories (code + Arabic label) — the UI's single
    source so its picker can't drift from the CHECK constraint."""
    from .models import CATEGORIES, CATEGORY_LABELS

    return jsonify({"items": [{"code": c, "label": CATEGORY_LABELS.get(c, c)} for c in CATEGORIES]})


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

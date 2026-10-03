"""/catalog and /commerce blueprints — browse, cart, checkout, orders, RFQ."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError

from ..common.errors import ApiError, BadRequest, Forbidden, NotFound, Unauthorized
from ..extensions import db
from ..identity.models import User
from ..identity.services.audit import emit as audit_emit
from ..identity.services.rbac import has_permission
from .models import Order
from .schemas import AddCartItemIn, CheckoutIn, RfqIn, RfqOfferIn, UpdateCartItemIn
from .services import cart as cart_svc
from .services import catalog as catalog_svc
from .services import orders as orders_svc
from .services import rfq as rfq_svc

bp = Blueprint("commerce", __name__)


def _parse(model_cls: Any) -> Any:
    try:
        return model_cls.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        raise BadRequest(f"Invalid payload: {e.errors()[0]['msg']}", code="validation_error") from e


def _uid() -> int:
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    return int(raw)


def _kind(uid: int) -> str:
    user = db.session.get(User, uid)
    return user.kind if user else ""


# ================================================================ catalog


@bp.get("/catalog/products")
@jwt_required()
def catalog_products():
    items = catalog_svc.browse(
        q=request.args.get("q"),
        category=request.args.get("category"),
        limit=min(int(request.args.get("limit", "100")), 500),
    )
    return jsonify({"items": items})


# ================================================================ cart


@bp.get("/commerce/cart")
@jwt_required()
def get_cart():
    return jsonify(cart_svc.serialize_cart(_uid()))


@bp.post("/commerce/cart/items")
@jwt_required()
def add_cart_item():
    payload = _parse(AddCartItemIn)
    item = cart_svc.add_item(customer_id=_uid(), offer_id=payload.offer_id, qty=Decimal(str(payload.qty)))
    return jsonify(cart_svc.serialize_cart(_uid())), 201 if item else 200


@bp.patch("/commerce/cart/items/<int:item_id>")
@jwt_required()
def update_cart_item(item_id: int):
    payload = _parse(UpdateCartItemIn)
    cart_svc.update_qty(customer_id=_uid(), item_id=item_id, qty=Decimal(str(payload.qty)))
    return jsonify(cart_svc.serialize_cart(_uid()))


@bp.delete("/commerce/cart/items/<int:item_id>")
@jwt_required()
def delete_cart_item(item_id: int):
    cart_svc.remove_item(customer_id=_uid(), item_id=item_id)
    return jsonify(cart_svc.serialize_cart(_uid()))


# ================================================================ checkout + orders


@bp.post("/commerce/checkout")
@jwt_required()
def checkout():
    payload = _parse(CheckoutIn)
    uid = _uid()
    order = orders_svc.checkout(customer_id=uid, payment_mode=payload.payment_mode)
    audit_emit("commerce.order.placed", actor_user_id=uid, target_type="order", target_id=order.id)
    return jsonify(orders_svc.serialize_order(order, for_customer=True)), 201


@bp.get("/commerce/orders")
@jwt_required()
def list_orders():
    orders = orders_svc.list_orders(_uid())
    return jsonify({"items": [orders_svc.serialize_order(o, for_customer=True) for o in orders]})


@bp.get("/commerce/orders/<int:order_id>")
@jwt_required()
def get_order(order_id: int):
    order = db.session.get(Order, order_id)
    if order is None:
        raise NotFound("Order not found", code="order_not_found")
    uid = _uid()
    is_admin = has_permission(uid, "user.read")  # admin/staff
    if not is_admin and order.customer_id != uid:
        raise Forbidden("ليس طلبك", code="forbidden")
    return jsonify(orders_svc.serialize_order(order, for_customer=not is_admin))


# ================================================================ RFQ


@bp.post("/commerce/rfqs")
@jwt_required()
def create_rfq():
    payload = _parse(RfqIn)
    uid = _uid()
    kind = _kind(uid)
    initiator_type = "supplier" if kind == "supplier" else "customer"
    rfq = rfq_svc.create_rfq(
        initiator_user_id=uid,
        initiator_type=initiator_type,
        product_id=payload.product_id,
        qty=Decimal(str(payload.qty)),
        deadline=payload.deadline,
        qualification_requirements=payload.qualification_requirements,
    )
    audit_emit("commerce.rfq.create", actor_user_id=uid, target_type="rfq", target_id=rfq.id)
    return jsonify(rfq_svc.serialize_rfq(rfq)), 201


@bp.get("/commerce/rfqs/<int:rfq_id>")
@jwt_required()
def get_rfq(rfq_id: int):
    from .models import Rfq

    rfq = db.session.get(Rfq, rfq_id)
    if rfq is None:
        raise NotFound("RFQ not found", code="rfq_not_found")
    return jsonify(rfq_svc.serialize_rfq(rfq))


@bp.post("/commerce/rfqs/<int:rfq_id>/offers")
@jwt_required()
def submit_rfq_offer(rfq_id: int):
    uid = _uid()
    if _kind(uid) != "supplier":
        raise Forbidden("المورد فقط يقدّم عروض RFQ", code="supplier_only")
    payload = _parse(RfqOfferIn)
    offer = rfq_svc.submit_offer(
        rfq_id=rfq_id, supplier_id=uid, unit_price=Decimal(str(payload.unit_price)), moq=Decimal(str(payload.moq))
    )
    audit_emit("commerce.rfq.offer", actor_user_id=uid, target_type="rfq_offer", target_id=offer.id)
    return jsonify({"offer_id": offer.id, "rfq_id": rfq_id}), 201


@bp.get("/commerce/rfqs/<int:rfq_id>/offers")
@jwt_required()
def list_rfq_offers(rfq_id: int):
    uid = _uid()
    is_admin = has_permission(uid, "user.read")
    offers = rfq_svc.list_offers(rfq_id=rfq_id, requester_id=uid, is_admin=is_admin)
    return jsonify({"items": offers})


# ================================================================ errors


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

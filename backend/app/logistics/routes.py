"""/logistics blueprint — slots, shipment tracking, delivery (EPIC 9).

- Slot catalogue + shipment status: `logistics.manage` (ops/admin).
- Location pings + delivery confirmation: `logistics.deliver` (the rep).
- Booking a slot and reading tracking: the order's customer, or staff.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError

from ..common.errors import ApiError, BadRequest, Forbidden, Unauthorized
from ..identity.services.rbac import has_permission, require_permission
from .schemas import AddLegIn, BookSlotIn, ConfirmDeliveryIn, CreateSlotIn, LocationIn, StatusIn
from .services import logistics as svc
from .services.logistics import ShortageInput

bp = Blueprint("logistics", __name__, url_prefix="/logistics")


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


def _require_order_owner_or_staff(order_id: int) -> None:
    uid = _uid()
    if has_permission(uid, "logistics.manage"):
        return
    order = svc._order_or_404(order_id)
    if order.customer_id != uid:
        raise Forbidden("غير مصرح", code="forbidden")


# ---------------------------------------------------------------- slots


@bp.post("/slots")
@require_permission("logistics.manage")
def create_slot():
    p = _parse(CreateSlotIn)
    slot = svc.create_slot(slot_date=p.slot_date, window=p.window, capacity=p.capacity)
    return jsonify(svc.serialize_slot(slot)), 201


@bp.get("/slots")
@jwt_required()
def list_slots():
    try:
        date_from = date.fromisoformat(request.args["from"])
        date_to = date.fromisoformat(request.args["to"])
    except (KeyError, ValueError) as e:
        raise BadRequest("from و to مطلوبان (YYYY-MM-DD)", code="range_required") from e
    return jsonify({"items": [svc.serialize_slot(s) for s in svc.available_slots(date_from=date_from, date_to=date_to)]})


@bp.post("/book")
@jwt_required()
def book():
    p = _parse(BookSlotIn)
    _require_order_owner_or_staff(p.order_id)
    shipment = svc.book_slot(
        order_id=p.order_id, slot_id=p.slot_id, carrier_type=p.carrier_type, actor_user_id=_uid()
    )
    # The customer gets the confirmation code to hand the rep on delivery.
    return jsonify(svc.serialize_shipment(shipment, include_code=True)), 201


# ---------------------------------------------------------------- tracking


@bp.get("/shipments")
@require_permission("logistics.manage")
def list_shipments():
    """Ops/admin shipment board — filter by status and create-date range.

    Replaces the old flow of typing an order number: every row exposes its
    allowed next transitions so the UI opens manage/confirm straight from the
    table. The confirmation code is never included in a list response."""
    status = request.args.get("status") or None
    date_from = date_to = None
    try:
        if request.args.get("from"):
            date_from = date.fromisoformat(request.args["from"])
        if request.args.get("to"):
            date_to = date.fromisoformat(request.args["to"])
    except ValueError as e:
        raise BadRequest("صيغة التاريخ غير صحيحة (YYYY-MM-DD)", code="bad_date") from e
    rows = svc.list_shipments(status=status, date_from=date_from, date_to=date_to)
    return jsonify({"items": [svc.serialize_shipment(s) for s in rows]})


@bp.get("/orders/<int:order_id>/shipment")
@jwt_required()
def track(order_id: int):
    _require_order_owner_or_staff(order_id)
    shipment = svc.shipment_for_order(order_id)
    return jsonify(svc.serialize_shipment(shipment))


@bp.post("/shipments/<int:shipment_id>/status")
@require_permission("logistics.manage")
def set_status(shipment_id: int):
    p = _parse(StatusIn)
    s = svc.update_status(shipment_id=shipment_id, status=p.status, actor_user_id=_uid())
    return jsonify({"id": s.id, "status": s.status})


@bp.post("/shipments/<int:shipment_id>/legs")
@require_permission("logistics.manage")
def add_leg(shipment_id: int):
    p = _parse(AddLegIn)
    leg = svc.add_leg(
        shipment_id=shipment_id,
        carrier_type=p.carrier_type,
        carrier_ref=p.carrier_ref,
        from_label=p.from_label,
        to_label=p.to_label,
    )
    return jsonify({"id": leg.id, "seq": leg.seq, "carrier_type": leg.carrier_type})


@bp.post("/shipments/<int:shipment_id>/location")
@require_permission("logistics.deliver")
def set_location(shipment_id: int):
    p = _parse(LocationIn)
    s = svc.update_location(shipment_id=shipment_id, lat=Decimal(str(p.lat)), lng=Decimal(str(p.lng)))
    return jsonify({"id": s.id, "status": s.status, "lat": str(s.current_lat), "lng": str(s.current_lng)})


@bp.post("/shipments/<int:shipment_id>/confirm")
@require_permission("logistics.deliver")
def confirm(shipment_id: int):
    p = _parse(ConfirmDeliveryIn)
    s = svc.confirm_delivery(
        shipment_id=shipment_id,
        delivered_by=_uid(),
        confirmation_code=p.confirmation_code,
        signature=p.signature,
        shortages=[
            ShortageInput(product_id=sh.product_id, qty=Decimal(str(sh.qty)), photo_url=sh.photo_url, note=sh.note)
            for sh in p.shortages
        ],
    )
    return jsonify(svc.serialize_shipment(s))


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

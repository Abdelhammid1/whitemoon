"""Delivery slots, shipment tracking, and delivery confirmation — EPIC 9."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from ...commerce.models import Order
from ...common.errors import BadRequest, Conflict, Forbidden, NotFound
from ...common.money import to_money
from ...extensions import db
from ...identity.services.audit import emit as audit_emit
from ...inventory.models import Product
from ..models import DeliveryShortage, DeliverySlot, Shipment


@dataclass(frozen=True)
class ShortageInput:
    product_id: int
    qty: Decimal
    photo_url: str | None = None
    note: str | None = None


def _now() -> datetime:
    return datetime.now(UTC)


def _gen_code() -> str:
    # 8 hex chars (~4.3e9 space) — a 6-digit code is brute-forceable and the
    # code is the delivery proof, so give it real entropy.
    return secrets.token_hex(4).upper()


# ---------------------------------------------------------------- slots (US-9.1)


def create_slot(*, slot_date: date, window: str, capacity: int) -> DeliverySlot:
    if capacity <= 0:
        raise BadRequest("السعة يجب أن تكون موجبة", code="bad_capacity")
    slot = DeliverySlot(slot_date=slot_date, window=window, capacity=capacity, booked=0)
    db.session.add(slot)
    db.session.commit()
    return slot


def available_slots(*, date_from: date, date_to: date) -> list[DeliverySlot]:
    """Only slots that are active and not yet full — a full slot is dropped
    from the list so it can't be chosen (US-9.1)."""
    rows = db.session.execute(
        select(DeliverySlot)
        .where(
            DeliverySlot.is_active.is_(True),
            DeliverySlot.slot_date >= date_from,
            DeliverySlot.slot_date <= date_to,
            DeliverySlot.booked < DeliverySlot.capacity,
        )
        .order_by(DeliverySlot.slot_date, DeliverySlot.window)
    ).scalars()
    return list(rows)


def _order_or_404(order_id: int) -> Order:
    order = db.session.get(Order, order_id)
    if order is None:
        raise NotFound("الطلب غير موجود", code="order_not_found")
    return order


def book_slot(
    *, order_id: int, slot_id: int, carrier_type: str = "internal", actor_user_id: int
) -> Shipment:
    """Attach an order to a delivery slot, respecting the slot's capacity.

    The slot row is locked (FOR UPDATE) and re-checked, so two concurrent
    bookings can never push a slot over capacity (no double-booking, US-9.1).
    """
    order = _order_or_404(order_id)
    if carrier_type not in ("internal", "external"):
        raise BadRequest("نوع الناقل غير صالح", code="bad_carrier")
    if order.status == "cancelled":
        raise Conflict("لا يمكن جدولة تسليم لطلب ملغى", code="order_cancelled")

    slot = db.session.execute(
        select(DeliverySlot).where(DeliverySlot.id == slot_id).with_for_update()
    ).scalar_one_or_none()
    if slot is None:
        raise NotFound("الموعد غير موجود", code="slot_not_found")
    if not slot.is_active:
        raise Conflict("الموعد غير متاح", code="slot_inactive")

    shipment = db.session.execute(
        select(Shipment).where(Shipment.order_id == order_id)
    ).scalar_one_or_none()
    if shipment is not None and shipment.status in ("delivered", "failed"):
        raise Conflict("الشحنة منتهية — لا يمكن إعادة الجدولة", code="shipment_closed")

    # Releasing a previously held slot (re-book) returns its capacity first.
    if shipment is not None and shipment.slot_id is not None and shipment.slot_id != slot_id:
        old = db.session.execute(
            select(DeliverySlot).where(DeliverySlot.id == shipment.slot_id).with_for_update()
        ).scalar_one()
        old.booked = max(0, old.booked - 1)

    already_on_this_slot = shipment is not None and shipment.slot_id == slot_id
    if not already_on_this_slot:
        if slot.booked >= slot.capacity:
            raise Conflict("الموعد ممتلئ", code="slot_full")
        slot.booked += 1

    if shipment is None:
        shipment = Shipment(
            order_id=order_id,
            slot_id=slot_id,
            carrier_type=carrier_type,
            status="scheduled",
            confirmation_code=_gen_code(),
        )
        db.session.add(shipment)
    else:
        shipment.slot_id = slot_id
        shipment.carrier_type = carrier_type

    audit_emit("logistics.slot.booked", actor_user_id=actor_user_id, target_type="order", target_id=order_id)
    db.session.commit()
    return shipment


# ---------------------------------------------------------------- tracking (US-9.2)


def _shipment_or_404(shipment_id: int) -> Shipment:
    s = db.session.get(Shipment, shipment_id)
    if s is None:
        raise NotFound("الشحنة غير موجودة", code="shipment_not_found")
    return s


def shipment_for_order(order_id: int) -> Shipment:
    s = db.session.execute(
        select(Shipment).where(Shipment.order_id == order_id)
    ).scalar_one_or_none()
    if s is None:
        raise NotFound("لا توجد شحنة لهذا الطلب", code="shipment_not_found")
    return s


_ALLOWED_TRANSITIONS = {
    "scheduled": {"shipped", "failed"},
    "shipped": {"in_transit", "delivered", "failed"},
    "in_transit": {"delivered", "failed"},
}


def update_status(*, shipment_id: int, status: str, actor_user_id: int) -> Shipment:
    s = _shipment_or_404(shipment_id)
    if status not in ("shipped", "in_transit", "delivered", "failed"):
        raise BadRequest("حالة غير صالحة", code="bad_status")
    if status == "delivered":
        raise BadRequest("استخدم تأكيد التسليم لإتمام التسليم", code="use_confirm_delivery")
    allowed = _ALLOWED_TRANSITIONS.get(s.status, set())
    if status not in allowed:
        raise Conflict(f"انتقال غير مسموح من {s.status} إلى {status}", code="bad_transition")
    s.status = status
    if status == "shipped":
        s.shipped_at = _now()
    audit_emit("logistics.shipment.status", actor_user_id=actor_user_id, target_type="shipment", target_id=s.id)
    db.session.commit()
    return s


def update_location(*, shipment_id: int, lat: Decimal, lng: Decimal) -> Shipment:
    s = _shipment_or_404(shipment_id)
    if s.status in ("delivered", "failed"):
        raise Conflict("الشحنة منتهية", code="shipment_closed")
    s.current_lat = lat
    s.current_lng = lng
    s.location_updated_at = _now()
    if s.status in ("scheduled", "shipped"):
        s.status = "in_transit"
    db.session.commit()
    return s


# ---------------------------------------------------------------- delivery (US-9.3)


def confirm_delivery(
    *,
    shipment_id: int,
    delivered_by: int,
    confirmation_code: str | None = None,
    signature: str | None = None,
    shortages: list[ShortageInput] | None = None,
) -> Shipment:
    """Close delivery with proof (a matching code OR a signature) and record
    any shortages with photos (the returns-log entries, US-9.3)."""
    s = _shipment_or_404(shipment_id)
    if s.status == "delivered":
        raise Conflict("تم التسليم بالفعل", code="already_delivered")
    if s.status == "failed":
        raise Conflict("الشحنة فاشلة", code="shipment_failed")

    has_code = confirmation_code is not None and confirmation_code.strip() != ""
    has_sig = signature is not None and signature.strip() != ""
    if not has_code and not has_sig:
        raise BadRequest("مطلوب رمز تأكيد أو توقيع", code="proof_required")
    if has_code and confirmation_code != s.confirmation_code:
        raise Forbidden("رمز التأكيد غير صحيح", code="bad_confirmation_code")

    for sh in shortages or []:
        if db.session.get(Product, sh.product_id) is None:
            raise NotFound(f"الصنف {sh.product_id} غير موجود", code="product_not_found")
        if to_money(sh.qty) <= 0:
            raise BadRequest("كمية النقص يجب أن تكون موجبة", code="bad_shortage_qty")
        db.session.add(
            DeliveryShortage(
                shipment_id=s.id,
                product_id=sh.product_id,
                qty=to_money(sh.qty),
                photo_url=sh.photo_url,
                note=sh.note,
            )
        )

    s.status = "delivered"
    s.delivered_at = _now()
    s.delivered_by = delivered_by
    if has_sig:
        s.signature = signature
    audit_emit("logistics.delivery.confirmed", actor_user_id=delivered_by, target_type="shipment", target_id=s.id)
    db.session.commit()
    return s


# ---------------------------------------------------------------- serializers


def serialize_slot(s: DeliverySlot) -> dict[str, Any]:
    return {
        "id": s.id,
        "slot_date": s.slot_date.isoformat(),
        "window": s.window,
        "capacity": s.capacity,
        "booked": s.booked,
        "remaining": s.capacity - s.booked,
        "is_active": s.is_active,
    }


def serialize_shipment(s: Shipment, *, include_code: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": s.id,
        "order_id": s.order_id,
        "slot_id": s.slot_id,
        "carrier_type": s.carrier_type,
        "status": s.status,
        "current_lat": str(s.current_lat) if s.current_lat is not None else None,
        "current_lng": str(s.current_lng) if s.current_lng is not None else None,
        "location_updated_at": s.location_updated_at.isoformat() if s.location_updated_at else None,
        "delivered_at": s.delivered_at.isoformat() if s.delivered_at else None,
        "shortages": [
            {"product_id": sh.product_id, "qty": str(sh.qty), "photo_url": sh.photo_url, "note": sh.note}
            for sh in s.shortages
        ],
    }
    if include_code:
        out["confirmation_code"] = s.confirmation_code
    return out

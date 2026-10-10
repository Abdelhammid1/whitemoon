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
from ..models import SHIPMENT_STATUSES, DeliveryShortage, DeliverySlot, Shipment, ShipmentLeg


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

# The order the UI should render the next-step buttons in, so a rep always
# sees scheduled → shipped → in_transit → delivered laid out left-to-right.
_TRANSITION_ORDER = ("shipped", "in_transit", "delivered", "failed")


def allowed_next(status: str) -> list[str]:
    """The statuses a shipment in `status` may move to, in display order.

    `delivered` is reachable here (it is a valid next state) but the route
    layer requires the confirmation-code flow to actually reach it — the UI
    uses this list to know *which* buttons to show, not to bypass that."""
    allowed = _ALLOWED_TRANSITIONS.get(status, set())
    return [s for s in _TRANSITION_ORDER if s in allowed]


def list_shipments(
    *,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 200,
) -> list[Shipment]:
    """Ops/admin shipment board, newest first, filtered by status + create date.

    No customer/supplier identity is loaded here — a shipment row carries only
    the order id, which staff are already entitled to see."""
    stmt = select(Shipment)
    if status:
        if status not in SHIPMENT_STATUSES:
            raise BadRequest("حالة غير صالحة", code="bad_status")
        stmt = stmt.where(Shipment.status == status)
    if date_from is not None:
        stmt = stmt.where(Shipment.created_at >= datetime(date_from.year, date_from.month, date_from.day, tzinfo=UTC))
    if date_to is not None:
        # inclusive end-of-day
        end = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=UTC)
        stmt = stmt.where(Shipment.created_at <= end)
    stmt = stmt.order_by(Shipment.id.desc()).limit(min(limit, 500))
    return list(db.session.execute(stmt).scalars().all())


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
    _notify_customer_shipment(s, status)
    return s


def _notify_customer_shipment(shipment: Shipment, status: str) -> None:
    """Notify the order's customer of a delivery-stage change (T-44). Never
    raises. Only the customer-visible stages carry a message."""
    stage = {
        "in_transit": ("طلبك في الطريق", "طلبك في الطريق إليك الآن — يمكنك تتبّع الشحنة."),
        "delivered": ("تم تسليم طلبك", "تم تسليم طلبك بنجاح. شكرًا لك."),
    }.get(status)
    if stage is None:
        return
    try:
        from ...commerce.models import Order
        from ...notifications.services import notify as notify_svc

        order = db.session.get(Order, shipment.order_id)
        if order is None:
            return
        notify_svc.notify(
            user_id=order.customer_id, title=stage[0], body=stage[1],
            type_="delivery_stage", channel="in_app",
        )
    except Exception:  # pragma: no cover - defensive
        pass


def update_location(*, shipment_id: int, lat: Decimal, lng: Decimal) -> Shipment:
    s = _shipment_or_404(shipment_id)
    if s.status in ("delivered", "failed"):
        raise Conflict("الشحنة منتهية", code="shipment_closed")
    s.current_lat = lat
    s.current_lng = lng
    s.location_updated_at = _now()
    became_in_transit = False
    if s.status in ("scheduled", "shipped"):
        s.status = "in_transit"
        became_in_transit = True
    db.session.commit()
    if became_in_transit:  # notify only on the transition, not every GPS ping
        _notify_customer_shipment(s, "in_transit")
    return s


# ---------------------------------------------------------------- delivery (US-9.3)


def add_leg(
    *,
    shipment_id: int,
    carrier_type: str,
    carrier_ref: str | None,
    from_label: str | None,
    to_label: str | None,
) -> ShipmentLeg:
    """Append a journey leg with its own carrier (US-9.4, T-05)."""
    s = _shipment_or_404(shipment_id)
    if carrier_type not in ("internal", "external"):
        raise BadRequest("نوع الناقل غير صالح", code="bad_carrier")
    next_seq = (max((leg.seq for leg in s.legs), default=0)) + 1
    leg = ShipmentLeg(
        shipment_id=s.id,
        seq=next_seq,
        carrier_type=carrier_type,
        carrier_ref=carrier_ref,
        from_label=from_label,
        to_label=to_label,
    )
    db.session.add(leg)
    db.session.commit()
    return leg


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
    _notify_customer_shipment(s, "delivered")
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
        "allowed_next": allowed_next(s.status),
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "shipped_at": s.shipped_at.isoformat() if s.shipped_at else None,
        "current_lat": str(s.current_lat) if s.current_lat is not None else None,
        "current_lng": str(s.current_lng) if s.current_lng is not None else None,
        "location_updated_at": s.location_updated_at.isoformat() if s.location_updated_at else None,
        "delivered_at": s.delivered_at.isoformat() if s.delivered_at else None,
        "shortages": [
            {"product_id": sh.product_id, "qty": str(sh.qty), "photo_url": sh.photo_url, "note": sh.note}
            for sh in s.shortages
        ],
        "legs": [
            {
                "seq": lg.seq,
                "carrier_type": lg.carrier_type,
                "carrier_ref": lg.carrier_ref,
                "from_label": lg.from_label,
                "to_label": lg.to_label,
                "status": lg.status,
            }
            for lg in s.legs
        ],
    }
    if include_code:
        out["confirmation_code"] = s.confirmation_code
    return out

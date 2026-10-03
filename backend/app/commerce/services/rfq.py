"""Request-for-quote workflow (US-1.4).

- A customer (or supplier, for a group offer) opens an RFQ for a product+qty
  with an optional deadline and qualification requirements.
- Suppliers submit priced offers.
- The initiator lists offers WITHOUT supplier identity (mediated by the
  company); only an admin sees the supplier behind each offer.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from ...common.errors import BadRequest, Conflict, Forbidden, NotFound
from ...common.money import to_money
from ...extensions import db
from ...inventory.models import Product
from ..models import Rfq, RfqOffer


def create_rfq(
    *,
    initiator_user_id: int,
    initiator_type: str,
    product_id: int,
    qty: Decimal,
    deadline: date | None = None,
    qualification_requirements: str | None = None,
) -> Rfq:
    if initiator_type not in ("customer", "supplier"):
        raise BadRequest("initiator_type must be customer|supplier", code="bad_initiator")
    if db.session.get(Product, product_id) is None:
        raise NotFound("Product not found", code="product_not_found")

    rfq = Rfq(
        number="PENDING",
        initiator_user_id=initiator_user_id,
        initiator_type=initiator_type,
        product_id=product_id,
        qty=to_money(qty),
        deadline=deadline,
        qualification_requirements=qualification_requirements,
        status="open",
    )
    db.session.add(rfq)
    db.session.flush()
    rfq.number = f"RFQ-{datetime.now(UTC).strftime('%Y%m')}-{rfq.id:06d}"
    db.session.commit()
    return rfq


def submit_offer(
    *, rfq_id: int, supplier_id: int, unit_price: Decimal, moq: Decimal = Decimal("0")
) -> RfqOffer:
    rfq = db.session.get(Rfq, rfq_id)
    if rfq is None:
        raise NotFound("RFQ not found", code="rfq_not_found")
    if rfq.status != "open":
        raise Conflict("RFQ is not open", code="rfq_not_open")
    existing = db.session.execute(
        select(RfqOffer).where(RfqOffer.rfq_id == rfq_id, RfqOffer.supplier_id == supplier_id)
    ).scalar_one_or_none()
    if existing is not None:
        existing.unit_price = to_money(unit_price)
        existing.moq = to_money(moq)
        db.session.commit()
        return existing
    offer = RfqOffer(rfq_id=rfq_id, supplier_id=supplier_id, unit_price=to_money(unit_price), moq=to_money(moq))
    db.session.add(offer)
    db.session.commit()
    return offer


def list_offers(*, rfq_id: int, requester_id: int, is_admin: bool) -> list[dict[str, Any]]:
    rfq = db.session.get(Rfq, rfq_id)
    if rfq is None:
        raise NotFound("RFQ not found", code="rfq_not_found")
    if not is_admin and rfq.initiator_user_id != requester_id:
        raise Forbidden("ليست طلبك", code="forbidden")
    out: list[dict[str, Any]] = []
    for o in rfq.offers:
        row: dict[str, Any] = {
            "offer_id": o.id,
            "unit_price": str(o.unit_price),
            "moq": str(o.moq),
            "submitted_at": o.submitted_at.isoformat(),
        }
        if is_admin:
            row["supplier_id"] = o.supplier_id  # admin only
        out.append(row)
    return out


def serialize_rfq(rfq: Rfq) -> dict[str, Any]:
    return {
        "id": rfq.id,
        "number": rfq.number,
        "product_id": rfq.product_id,
        "qty": str(rfq.qty),
        "deadline": rfq.deadline.isoformat() if rfq.deadline else None,
        "qualification_requirements": rfq.qualification_requirements,
        "status": rfq.status,
        "offer_count": len(rfq.offers),
    }

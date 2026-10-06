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


def serialize_rfq(rfq: Rfq, *, viewer_id: int | None = None) -> dict[str, Any]:
    """Serialize an RFQ for its initiator, a supplier, or an admin.

    Never includes the initiator's identity — the company mediates the RFQ, so
    a supplier browsing the inbox sees only the product, qty, deadline and
    requirements, exactly as `list_offers` hides the supplier from the customer.
    `viewer_id`, when it is a supplier, adds `my_offer` so the inbox can show
    'you already quoted' without revealing anyone else's price."""
    product = db.session.get(Product, rfq.product_id)
    out: dict[str, Any] = {
        "id": rfq.id,
        "number": rfq.number,
        "product_id": rfq.product_id,
        "product_name": product.name_ar if product else None,
        "qty": str(rfq.qty),
        "deadline": rfq.deadline.isoformat() if rfq.deadline else None,
        "qualification_requirements": rfq.qualification_requirements,
        "status": rfq.status,
        "offer_count": len(rfq.offers),
    }
    if viewer_id is not None:
        mine = next((o for o in rfq.offers if o.supplier_id == viewer_id), None)
        if mine is not None:
            out["my_offer"] = {"unit_price": str(mine.unit_price), "moq": str(mine.moq)}
    return out


def list_rfqs(*, requester_id: int, kind: str, is_admin: bool) -> list[dict[str, Any]]:
    """RFQ list scoped to the viewer:

    - admin → every RFQ;
    - supplier → the open inbox (RFQs still accepting offers), with `my_offer`
      filled when this supplier already quoted — initiator identity never shown;
    - customer → only the RFQs they opened.
    """
    stmt = select(Rfq).order_by(Rfq.id.desc()).limit(500)
    if is_admin:
        rfqs = db.session.execute(stmt).scalars().all()
        return [serialize_rfq(r) for r in rfqs]
    if kind == "supplier":
        rfqs = db.session.execute(stmt.where(Rfq.status == "open")).scalars().all()
        return [serialize_rfq(r, viewer_id=requester_id) for r in rfqs]
    rfqs = db.session.execute(stmt.where(Rfq.initiator_user_id == requester_id)).scalars().all()
    return [serialize_rfq(r) for r in rfqs]

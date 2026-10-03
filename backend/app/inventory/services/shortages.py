"""Shortages + returns with responsible-party accounting (US-4.4).

Resolving a shortage posts the matching journal:
  - responsible = supplier         → shortage.resolved.supplier
  - responsible = channel_partner  → shortage.resolved.partner
                                     (agent→1141 / branch→1142 via partner_kind)
  - responsible = unallocated      → shortage.resolved.unallocated (5310 loss)
Then the responsible party's inventory is reduced.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from ...accounting.services import events as journal
from ...common.errors import BadRequest, Conflict, NotFound
from ...common.money import to_money
from ...extensions import db
from ...identity.models import ChannelPartnerProfile
from ..models import Product, Shortage

MIN_REASON_LEN = 5


def report_shortage(
    *,
    reporter_user_id: int,
    supplier_id: int,
    product_id: int,
    qty: Decimal,
    unit_cost: Decimal,
    transfer_order_id: int | None = None,
    evidence_s3_keys: list[str] | None = None,
) -> Shortage:
    if to_money(qty) <= 0:
        raise BadRequest("qty must be positive", code="bad_qty")
    product = db.session.get(Product, product_id)
    if product is None:
        raise NotFound("Product not found", code="product_not_found")
    if not evidence_s3_keys:
        raise BadRequest("evidence images are required", code="evidence_required")

    shortage = Shortage(
        reporter_user_id=reporter_user_id,
        supplier_id=supplier_id,
        product_id=product_id,
        qty=to_money(qty),
        unit_cost=to_money(unit_cost),
        transfer_order_id=transfer_order_id,
        evidence_s3_keys=evidence_s3_keys,
        status="pending",
    )
    db.session.add(shortage)
    db.session.commit()
    return shortage


def resolve_shortage(
    *,
    shortage_id: int,
    responsible_party_type: str,
    responsible_party_id: int | None,
    reason: str,
    resolved_by: int,
    entry_date: date | None = None,
) -> Shortage:
    if not reason or len(reason.strip()) < MIN_REASON_LEN:
        raise BadRequest("reason required (≥5 chars)", code="reason_required")
    shortage = db.session.get(Shortage, shortage_id)
    if shortage is None:
        raise NotFound("Shortage not found", code="shortage_not_found")
    if shortage.status != "pending":
        raise Conflict("shortage already resolved", code="already_resolved")

    product = db.session.get(Product, shortage.product_id)
    assert product is not None  # FK guarantees it
    category = product.category
    value = to_money(shortage.qty) * to_money(shortage.unit_cost)

    context: dict[str, Any] = {"cost": value, "category": category}

    if responsible_party_type == "supplier":
        event_type = "shortage.resolved.supplier"
    elif responsible_party_type == "channel_partner":
        if responsible_party_id is None:
            raise BadRequest("partner id required", code="partner_id_required")
        partner = db.session.get(ChannelPartnerProfile, responsible_party_id)
        if partner is None:
            raise NotFound("Channel partner not found", code="partner_not_found")
        context["partner_kind"] = partner.type  # 'agent' | 'branch'
        event_type = "shortage.resolved.partner"
    elif responsible_party_type == "unallocated":
        event_type = "shortage.resolved.unallocated"
    else:
        raise BadRequest(
            "responsible_party_type must be supplier/channel_partner/unallocated",
            code="bad_responsible_type",
        )

    posting = journal.post(
        event_type=event_type,
        entry_date=entry_date or date.today(),
        description=f"حسم نقص #{shortage.id} على {responsible_party_type}",
        context=context,
        source_event_id=shortage.id,
        posted_by=resolved_by,
    )

    shortage.responsible_party_type = responsible_party_type
    shortage.responsible_party_id = responsible_party_id
    shortage.resolution_notes = reason.strip()
    shortage.resolved_by = resolved_by
    shortage.resolved_at = datetime.now(UTC)
    shortage.journal_entry_id = posting.entry_id
    shortage.status = "resolved"
    db.session.commit()
    return shortage


def list_shortages(*, status: str | None = None, limit: int = 100) -> list[Shortage]:
    stmt = select(Shortage).order_by(Shortage.id.desc()).limit(limit)
    if status:
        stmt = stmt.where(Shortage.status == status)
    return list(db.session.execute(stmt).scalars().all())


def serialize(shortage: Shortage) -> dict[str, Any]:
    return {
        "id": shortage.id,
        "product_id": shortage.product_id,
        "supplier_id": shortage.supplier_id,
        "qty": str(shortage.qty),
        "unit_cost": str(shortage.unit_cost),
        "status": shortage.status,
        "responsible_party_type": shortage.responsible_party_type,
        "responsible_party_id": shortage.responsible_party_id,
        "journal_entry_id": shortage.journal_entry_id,
        "transfer_order_id": shortage.transfer_order_id,
    }

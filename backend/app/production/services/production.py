"""Manufacturing-order lifecycle — EPIC 7.

create → advance through predefined stages → complete. Completing deducts the
materials from stock, adds the finished good, and posts
`production.mo.closed` automatically (US-7.2). All money is EGP.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text

from ...accounting.services import events as journal
from ...common.errors import BadRequest, Conflict, NotFound
from ...common.money import to_money
from ...extensions import db
from ...identity.services.audit import emit as audit_emit
from ...inventory.models import Product
from ...inventory.services import stock
from ..models import ManufacturingOrder, MOMaterial, MOStage

_MO_LOCK_NS = 0x4D4F  # "MO"


@dataclass(frozen=True)
class MaterialInput:
    product_id: int
    qty: Decimal
    unit_cost: Decimal


def _now() -> datetime:
    return datetime.now(UTC)


def _number() -> str:
    return f"MO-{_now().strftime('%Y%m')}-"


def _lock_mo(mo_id: int) -> None:
    db.session.execute(
        text("SELECT pg_advisory_xact_lock(:ns, :mid)"), {"ns": _MO_LOCK_NS, "mid": mo_id}
    )


def _get(mo_id: int) -> ManufacturingOrder:
    mo = db.session.get(ManufacturingOrder, mo_id)
    if mo is None:
        raise NotFound("أمر التصنيع غير موجود", code="mo_not_found")
    return mo


def create_mo(
    *,
    owner_id: int,
    output_product_id: int,
    output_qty: Decimal,
    materials: list[MaterialInput],
    stages: list[str],
    location_type: str = "supplier",
    location_id: int | None = None,
    actor_user_id: int,
) -> ManufacturingOrder:
    if not materials:
        raise BadRequest("يجب تحديد خامة واحدة على الأقل", code="materials_required")
    if not stages:
        raise BadRequest("يجب تحديد مرحلة واحدة على الأقل", code="stages_required")
    output_qty = to_money(output_qty)
    if output_qty <= 0:
        raise BadRequest("كمية المنتج يجب أن تكون موجبة", code="bad_output_qty")
    if db.session.get(Product, output_product_id) is None:
        raise NotFound("المنتج النهائي غير موجود", code="output_product_not_found")

    total_cost = Decimal("0")
    for m in materials:
        if db.session.get(Product, m.product_id) is None:
            raise NotFound(f"الخامة {m.product_id} غير موجودة", code="material_not_found")
        if to_money(m.qty) <= 0:
            raise BadRequest("كمية الخامة يجب أن تكون موجبة", code="bad_material_qty")
        total_cost += to_money(m.qty) * to_money(m.unit_cost)

    mo = ManufacturingOrder(
        number="PENDING",
        owner_id=owner_id,
        output_product_id=output_product_id,
        output_qty=output_qty,
        location_type=location_type,
        location_id=location_id,
        status="draft",
        total_material_cost=to_money(total_cost),
    )
    db.session.add(mo)
    db.session.flush()
    mo.number = f"{_number()}{mo.id:06d}"

    for i, name in enumerate(stages, start=1):
        db.session.add(MOStage(mo_id=mo.id, seq=i, name=name, status="pending"))
    for m in materials:
        db.session.add(
            MOMaterial(
                mo_id=mo.id,
                product_id=m.product_id,
                qty=to_money(m.qty),
                unit_cost=to_money(m.unit_cost),
            )
        )
    audit_emit("production.mo.created", actor_user_id=actor_user_id, target_type="mo", target_id=mo.id)
    db.session.commit()
    return mo


def advance_stage(*, mo_id: int, actor_user_id: int) -> MOStage:
    """Mark the next pending stage done (US-7.1)."""
    _lock_mo(mo_id)
    mo = _get(mo_id)
    if mo.status in ("completed", "cancelled"):
        raise Conflict(f"الأمر في حالة {mo.status}", code="mo_not_open")
    nxt = db.session.execute(
        select(MOStage)
        .where(MOStage.mo_id == mo_id, MOStage.status == "pending")
        .order_by(MOStage.seq)
        .limit(1)
    ).scalar_one_or_none()
    if nxt is None:
        raise Conflict("كل المراحل مكتملة", code="no_pending_stage")
    nxt.status = "done"
    nxt.done_at = _now()
    if mo.status == "draft":
        mo.status = "in_progress"
        mo.started_at = _now()
    audit_emit("production.mo.stage_advanced", actor_user_id=actor_user_id, target_type="mo", target_id=mo.id)
    db.session.commit()
    return nxt


def complete(*, mo_id: int, posted_by: int, entry_date: date | None = None) -> ManufacturingOrder:
    """Close the order: consume materials, produce the finished good, and post
    the inventory/accounting journal (US-7.2). Idempotent under a per-order
    lock — a second completion is rejected, never double-posted."""
    _lock_mo(mo_id)
    mo = _get(mo_id)
    if mo.status == "completed":
        raise Conflict("الأمر مكتمل بالفعل", code="mo_already_completed")
    if mo.status == "cancelled":
        raise Conflict("الأمر ملغى", code="mo_cancelled")

    pending = db.session.execute(
        select(MOStage).where(MOStage.mo_id == mo_id, MOStage.status == "pending")
    ).first()
    if pending is not None:
        raise BadRequest("لا يمكن الإغلاق قبل إتمام كل المراحل", code="stages_incomplete")

    materials = list(
        db.session.execute(select(MOMaterial).where(MOMaterial.mo_id == mo_id)).scalars()
    )
    # Check availability for every material before moving any stock.
    for m in materials:
        stock.require_available(
            supplier_id=mo.owner_id,
            product_id=m.product_id,
            location_type=mo.location_type,
            location_id=mo.location_id,
            qty=to_money(m.qty),
        )
    for m in materials:
        stock.adjust(
            supplier_id=mo.owner_id,
            product_id=m.product_id,
            location_type=mo.location_type,
            location_id=mo.location_id,
            delta=-to_money(m.qty),
        )
    # Add the finished good.
    stock.adjust(
        supplier_id=mo.owner_id,
        product_id=mo.output_product_id,
        location_type=mo.location_type,
        location_id=mo.location_id,
        delta=to_money(mo.output_qty),
    )

    out_product = db.session.get(Product, mo.output_product_id)
    assert out_product is not None
    posting = journal.post(
        event_type="production.mo.closed",
        entry_date=entry_date or _now().date(),
        description=f"إغلاق أمر تصنيع {mo.number}",
        context={
            "cost": to_money(mo.total_material_cost),
            "category": out_product.category,
            "location_type": mo.location_type,
        },
        source_event_id=mo.id,
        posted_by=posted_by,
    )

    mo.status = "completed"
    mo.completed_at = _now()
    mo.journal_entry_id = posting.entry_id
    audit_emit("production.mo.completed", actor_user_id=posted_by, target_type="mo", target_id=mo.id)
    db.session.commit()
    return mo


def cancel(*, mo_id: int, actor_user_id: int) -> ManufacturingOrder:
    _lock_mo(mo_id)
    mo = _get(mo_id)
    if mo.status == "completed":
        raise Conflict("لا يمكن إلغاء أمر مكتمل", code="mo_completed")
    if mo.status == "cancelled":
        return mo
    mo.status = "cancelled"
    audit_emit("production.mo.cancelled", actor_user_id=actor_user_id, target_type="mo", target_id=mo.id)
    db.session.commit()
    return mo


def get_mo(mo_id: int) -> ManufacturingOrder:
    return _get(mo_id)


def list_mos(*, owner_id: int | None = None, limit: int = 100) -> list[ManufacturingOrder]:
    stmt = select(ManufacturingOrder).order_by(ManufacturingOrder.id.desc()).limit(limit)
    if owner_id is not None:
        stmt = stmt.where(ManufacturingOrder.owner_id == owner_id)
    return list(db.session.execute(stmt).scalars())


def serialize(mo: ManufacturingOrder) -> dict[str, Any]:
    return {
        "id": mo.id,
        "number": mo.number,
        "owner_id": mo.owner_id,
        "output_product_id": mo.output_product_id,
        "output_qty": str(mo.output_qty),
        "location_type": mo.location_type,
        "location_id": mo.location_id,
        "status": mo.status,
        "total_material_cost": str(mo.total_material_cost),
        "journal_entry_id": mo.journal_entry_id,
        "stages": [
            {"seq": s.seq, "name": s.name, "status": s.status} for s in mo.stages
        ],
        "materials": [
            {"product_id": m.product_id, "qty": str(m.qty), "unit_cost": str(m.unit_cost)}
            for m in mo.materials
        ],
    }

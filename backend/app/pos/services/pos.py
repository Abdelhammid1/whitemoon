"""POS sell + batch settlement — EPIC 8.

A sale deducts stock from the shared inventory table immediately (US-8.2,
single source of truth) and is left `unposted`. A settlement run aggregates
every unposted sale's revenue by category and posts `pos.sale.batch` once per
category, so POS accounting is batched rather than real-time.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text

from ...accounting.services import events as journal
from ...common.errors import BadRequest, NotFound
from ...common.money import to_money
from ...extensions import db
from ...identity.services.audit import emit as audit_emit
from ...inventory.models import Product, SupplierOffer
from ...inventory.services import stock
from ..models import PosBatch, PosSale, PosSaleLine

# Single advisory-lock key: settlement is serialised globally so two runs
# can't post the same unposted sales twice.
_POS_BATCH_LOCK = 0x504F5342  # "POSB" truncated


@dataclass(frozen=True)
class SaleLineInput:
    product_id: int
    supplier_id: int
    qty: Decimal
    # No price here: the POS unit price is derived server-side from the
    # supplier's active offer, never accepted from the client (anti-tamper).


def _now() -> datetime:
    return datetime.now(UTC)


def _number() -> str:
    return f"POS-{_now().strftime('%Y%m%d')}-"


def create_sale(
    *,
    cashier_id: int,
    location_type: str,
    location_id: int | None,
    lines: list[SaleLineInput],
) -> PosSale:
    """Record a POS sale and deduct stock immediately. Leaves the sale
    unposted — the journal is deferred to the batch settlement."""
    if not lines:
        raise BadRequest("لا توجد أصناف في البيع", code="empty_sale")

    resolved: list[tuple[SaleLineInput, str, Decimal, Decimal]] = []
    total = Decimal("0")
    for li in lines:
        product = db.session.get(Product, li.product_id)
        if product is None:
            raise NotFound(f"الصنف {li.product_id} غير موجود", code="product_not_found")
        qty = to_money(li.qty)
        if qty <= 0:
            raise BadRequest("الكمية يجب أن تكون موجبة", code="bad_qty")
        # Server-derived price: the supplier's active offer for this product.
        offer = db.session.execute(
            select(SupplierOffer).where(
                SupplierOffer.supplier_id == li.supplier_id,
                SupplierOffer.product_id == li.product_id,
                SupplierOffer.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if offer is None:
            raise BadRequest(
                f"لا يوجد عرض سعر فعّال للصنف {li.product_id}", code="no_active_offer"
            )
        unit = to_money(offer.unit_price)
        line_total = qty * unit
        resolved.append((li, product.category, unit, line_total))
        total += line_total

    # Shared inventory: check availability for every line, then deduct.
    for li, _cat, _unit, _lt in resolved:
        stock.require_available(
            supplier_id=li.supplier_id,
            product_id=li.product_id,
            location_type=location_type,
            location_id=location_id,
            qty=to_money(li.qty),
        )
    for li, _cat, _unit, _lt in resolved:
        stock.adjust(
            supplier_id=li.supplier_id,
            product_id=li.product_id,
            location_type=location_type,
            location_id=location_id,
            delta=-to_money(li.qty),
        )

    sale = PosSale(
        number="PENDING",
        cashier_id=cashier_id,
        location_type=location_type,
        location_id=location_id,
        total=to_money(total),
        status="completed",
        posted=False,
    )
    db.session.add(sale)
    db.session.flush()
    sale.number = f"{_number()}{sale.id:06d}"
    for li, cat, unit, line_total in resolved:
        db.session.add(
            PosSaleLine(
                sale_id=sale.id,
                product_id=li.product_id,
                supplier_id=li.supplier_id,
                category=cat,
                qty=to_money(li.qty),
                unit_price=to_money(unit),
                line_total=to_money(line_total),
            )
        )
    audit_emit("pos.sale.created", actor_user_id=cashier_id, target_type="pos_sale", target_id=sale.id)
    db.session.commit()
    return sale


def settle_batch(*, posted_by: int, entry_date: date | None = None) -> PosBatch:
    """Post every unposted POS sale in one batch (US-8.2). One journal entry
    per category. Serialised with an advisory lock so sales are never
    double-posted."""
    db.session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _POS_BATCH_LOCK})

    sales = list(
        db.session.execute(
            select(PosSale).where(PosSale.posted.is_(False), PosSale.status == "completed")
        ).scalars()
    )
    if not sales:
        raise BadRequest("لا توجد مبيعات غير مرحّلة", code="nothing_to_settle")

    revenue_by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    total = Decimal("0")
    for s in sales:
        for ln in s.lines:
            revenue_by_category[ln.category] += to_money(ln.line_total)
        total += to_money(s.total)

    batch = PosBatch(posted_by=posted_by, sale_count=len(sales), total=to_money(total))
    db.session.add(batch)
    db.session.flush()

    first_entry_id: int | None = None
    for category, amount in revenue_by_category.items():
        if amount <= 0:
            continue
        posting = journal.post(
            event_type="pos.sale.batch",
            entry_date=entry_date or _now().date(),
            description=f"تسوية مبيعات نقطة البيع #{batch.id} — {category}",
            context={"amount": to_money(amount), "category": category},
            source_event_id=batch.id,
            posted_by=posted_by,
        )
        if first_entry_id is None:
            first_entry_id = posting.entry_id
    batch.journal_entry_id = first_entry_id

    for s in sales:
        s.posted = True
        s.batch_id = batch.id

    audit_emit("pos.batch.settled", actor_user_id=posted_by, target_type="pos_batch", target_id=batch.id)
    db.session.commit()
    return batch


def get_sale(sale_id: int, *, only_cashier_id: int | None = None) -> PosSale:
    s = db.session.get(PosSale, sale_id)
    if s is None:
        raise NotFound("البيع غير موجود", code="pos_sale_not_found")
    # A cashier may only read their own sales; a settler (None) sees all.
    if only_cashier_id is not None and s.cashier_id != only_cashier_id:
        raise NotFound("البيع غير موجود", code="pos_sale_not_found")
    return s


def list_sales(
    *, posted: bool | None = None, only_cashier_id: int | None = None, limit: int = 100
) -> list[PosSale]:
    stmt = select(PosSale).order_by(PosSale.id.desc()).limit(limit)
    if posted is not None:
        stmt = stmt.where(PosSale.posted.is_(posted))
    if only_cashier_id is not None:
        stmt = stmt.where(PosSale.cashier_id == only_cashier_id)
    return list(db.session.execute(stmt).scalars())


def serialize_sale(s: PosSale) -> dict[str, Any]:
    return {
        "id": s.id,
        "number": s.number,
        "cashier_id": s.cashier_id,
        "location_type": s.location_type,
        "location_id": s.location_id,
        "total": str(s.total),
        "status": s.status,
        "posted": s.posted,
        "batch_id": s.batch_id,
        "lines": [
            {
                "product_id": ln.product_id,
                "category": ln.category,
                "qty": str(ln.qty),
                "unit_price": str(ln.unit_price),
                "line_total": str(ln.line_total),
            }
            for ln in s.lines
        ],
    }


def serialize_batch(b: PosBatch) -> dict[str, Any]:
    return {
        "id": b.id,
        "posted_by": b.posted_by,
        "posted_at": b.posted_at.isoformat(),
        "sale_count": b.sale_count,
        "total": str(b.total),
        "journal_entry_id": b.journal_entry_id,
    }

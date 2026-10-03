"""Transfer orders — first-class entity with auto journals (US-4.2).

Lifecycle: draft → issued → received. Each operational step posts the
matching journal via the accounting event-map:
  - issue   → inventory.transfer.issued   (dr 9100, cr source inventory)
  - receive → inventory.transfer.received (dr dest inventory, cr 9100)

A transfer carries one category (food OR clothing) so the by_location /
by_category account resolution stays unambiguous; mixed-category moves
must be split into separate transfer orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from ...accounting.services import events as journal
from ...common.errors import BadRequest, Conflict, NotFound
from ...common.money import to_money
from ...extensions import db
from ..models import Product, TransferOrder, TransferOrderLine
from . import stock


@dataclass(frozen=True)
class LineInput:
    product_id: int
    qty: Decimal
    unit_cost: Decimal


def _order_category(lines: list[LineInput]) -> str:
    categories: set[str] = set()
    for li in lines:
        product = db.session.get(Product, li.product_id)
        if product is None:
            raise NotFound(f"Product {li.product_id} not found", code="product_not_found")
        categories.add(product.category)
    if len(categories) != 1:
        raise BadRequest(
            "a transfer order must contain one category only",
            code="mixed_category_transfer",
        )
    return next(iter(categories))


def _total_cost(lines: list[LineInput]) -> Decimal:
    return sum(
        (to_money(li.qty) * to_money(li.unit_cost) for li in lines),
        start=Decimal("0"),
    )


def create_transfer_order(
    *,
    supplier_id: int,
    from_location_type: str,
    from_location_id: int | None,
    to_location_type: str,
    to_location_id: int | None,
    lines: list[LineInput],
    initiated_by: int,
) -> TransferOrder:
    if not lines:
        raise BadRequest("at least one line required", code="no_lines")
    _order_category(lines)  # validates single category + products exist

    order = TransferOrder(
        number="PENDING",
        supplier_id=supplier_id,
        from_location_type=from_location_type,
        from_location_id=from_location_id,
        to_location_type=to_location_type,
        to_location_id=to_location_id,
        status="draft",
        initiated_by=initiated_by,
    )
    db.session.add(order)
    db.session.flush()
    order.number = f"TRF-{datetime.now(UTC).strftime('%Y%m')}-{order.id:06d}"
    for li in lines:
        db.session.add(
            TransferOrderLine(
                transfer_order_id=order.id,
                product_id=li.product_id,
                qty=to_money(li.qty),
                unit_cost=to_money(li.unit_cost),
            )
        )
    db.session.commit()
    return order


def _lines_of(order: TransferOrder) -> list[LineInput]:
    return [
        LineInput(product_id=ln.product_id, qty=ln.qty, unit_cost=ln.unit_cost)
        for ln in order.lines
    ]


def issue(*, order_id: int, issued_by: int, entry_date: date | None = None) -> TransferOrder:
    order = db.session.get(TransferOrder, order_id)
    if order is None:
        raise NotFound("Transfer order not found", code="transfer_not_found")
    if order.status != "draft":
        raise Conflict(f"cannot issue from status {order.status}", code="bad_status")

    lines = _lines_of(order)
    category = _order_category(lines)
    total = _total_cost(lines)

    # Decrement source stock per line (physical move out).
    for li in lines:
        stock.require_available(
            supplier_id=order.supplier_id,
            product_id=li.product_id,
            location_type=order.from_location_type,
            location_id=order.from_location_id,
            qty=li.qty,
        )
    for li in lines:
        stock.adjust(
            supplier_id=order.supplier_id,
            product_id=li.product_id,
            location_type=order.from_location_type,
            location_id=order.from_location_id,
            delta=-to_money(li.qty),
        )

    posting = journal.post(
        event_type="inventory.transfer.issued",
        entry_date=entry_date or date.today(),
        description=f"إصدار إذن تحويل {order.number}",
        context={
            "cost": total,
            "category": category,
            "location_type": order.from_location_type,
        },
        source_event_id=order.id,
        posted_by=issued_by,
    )

    order.status = "issued"
    order.issued_by = issued_by
    order.issued_at = datetime.now(UTC)
    order.issue_entry_id = posting.entry_id
    db.session.commit()
    return order


def receive(*, order_id: int, received_by: int, entry_date: date | None = None) -> TransferOrder:
    order = db.session.get(TransferOrder, order_id)
    if order is None:
        raise NotFound("Transfer order not found", code="transfer_not_found")
    if order.status != "issued":
        raise Conflict(f"cannot receive from status {order.status}", code="bad_status")

    lines = _lines_of(order)
    category = _order_category(lines)
    total = _total_cost(lines)

    for li in lines:
        stock.adjust(
            supplier_id=order.supplier_id,
            product_id=li.product_id,
            location_type=order.to_location_type,
            location_id=order.to_location_id,
            delta=to_money(li.qty),
        )

    posting = journal.post(
        event_type="inventory.transfer.received",
        entry_date=entry_date or date.today(),
        description=f"استلام إذن تحويل {order.number}",
        context={
            "cost": total,
            "category": category,
            "location_type": order.to_location_type,
        },
        source_event_id=order.id,
        posted_by=received_by,
    )

    order.status = "received"
    order.received_by = received_by
    order.received_at = datetime.now(UTC)
    order.receive_entry_id = posting.entry_id
    db.session.commit()
    return order


def cancel(*, order_id: int) -> TransferOrder:
    order = db.session.get(TransferOrder, order_id)
    if order is None:
        raise NotFound("Transfer order not found", code="transfer_not_found")
    if order.status != "draft":
        raise Conflict("only draft orders can be cancelled", code="bad_status")
    order.status = "cancelled"
    order.cancelled_at = datetime.now(UTC)
    db.session.commit()
    return order


def serialize(order: TransferOrder) -> dict[str, Any]:
    return {
        "id": order.id,
        "number": order.number,
        "supplier_id": order.supplier_id,
        "from_location_type": order.from_location_type,
        "from_location_id": order.from_location_id,
        "to_location_type": order.to_location_type,
        "to_location_id": order.to_location_id,
        "status": order.status,
        "issue_entry_id": order.issue_entry_id,
        "receive_entry_id": order.receive_entry_id,
        "lines": [
            {
                "product_id": ln.product_id,
                "qty": str(ln.qty),
                "unit_cost": str(ln.unit_cost),
            }
            for ln in order.lines
        ],
    }

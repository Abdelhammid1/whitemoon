"""Executive dashboard aggregation — read-only, across domains."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from ...comm.models import Conversation, Message
from ...commerce.models import Order
from ...extensions import db
from ...inventory.models import StockBalance
from ...logistics.models import Shipment
from ...pos.models import PosSale
from ...production.models import ManufacturingOrder
from ...sales.models import CustomerDue


def _count_by(column: Any) -> dict[str, int]:
    rows = db.session.execute(select(column, func.count()).group_by(column)).all()
    return {str(k): int(v) for k, v in rows}


def _sum(column: Any, *where: Any) -> Decimal:
    stmt = select(func.coalesce(func.sum(column), 0))
    for w in where:
        stmt = stmt.where(w)
    return Decimal(str(db.session.execute(stmt).scalar_one()))


def dashboard() -> dict[str, Any]:
    realized = ("confirmed", "fulfilled")

    low_stock = db.session.execute(
        select(func.count())
        .select_from(StockBalance)
        .where(
            StockBalance.reorder_point.is_not(None),
            StockBalance.on_hand <= StockBalance.reorder_point,
        )
    ).scalar_one()
    flagged_convos = db.session.execute(
        select(func.count(func.distinct(Message.conversation_id))).where(Message.status == "blocked")
    ).scalar_one()
    open_convos = db.session.execute(
        select(func.count()).select_from(Conversation).where(Conversation.status == "open")
    ).scalar_one()

    return {
        "currency": "EGP",
        "sales": {
            "orders_by_status": _count_by(Order.status),
            "realized_revenue": str(_sum(Order.total_cash, Order.status.in_(realized))),
        },
        "collection": {
            "dues_by_status": _count_by(CustomerDue.status),
            "outstanding": str(_sum(CustomerDue.amount, CustomerDue.status == "open")),
            "defaulted": str(_sum(CustomerDue.amount, CustomerDue.status == "defaulted")),
        },
        "inventory": {"low_stock_slots": int(low_stock)},
        "pos": {
            "unposted_total": str(
                _sum(PosSale.total, PosSale.posted.is_(False), PosSale.status == "completed")
            ),
        },
        "logistics": {"shipments_by_status": _count_by(Shipment.status)},
        "production": {"orders_by_status": _count_by(ManufacturingOrder.status)},
        "communication": {
            "open_conversations": int(open_convos),
            "flagged_conversations": int(flagged_convos),
        },
    }

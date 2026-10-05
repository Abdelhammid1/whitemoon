"""Executive dashboard aggregation — read-only, across domains."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from ...comm.models import Conversation, Message
from ...commerce.models import Order
from ...extensions import db
from ...inventory.models import StockBalance
from ...logistics.models import Shipment
from ...pos.models import PosSale
from ...production.models import ManufacturingOrder
from ...sales.models import CustomerCreditTier, CustomerDue

_CAIRO = ZoneInfo("Africa/Cairo")


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

    # Open (not yet fulfilled/cancelled) orders — the "الطلبات المفتوحة" tile.
    open_orders = db.session.execute(
        select(func.count())
        .select_from(Order)
        .where(Order.status.in_(("pending", "confirmed")))
    ).scalar_one()

    # Daily sales for the last 7 days (Africa/Cairo), oldest → today. Cancelled
    # orders excluded. The last element's total is "today's sales".
    today = datetime.now(_CAIRO).date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    rows = db.session.execute(
        select(func.date(Order.placed_at), func.coalesce(func.sum(Order.total_cash), 0))
        .where(Order.status != "cancelled")
        .group_by(func.date(Order.placed_at))
    ).all()
    by_date = {str(d): Decimal(str(v)) for d, v in rows}
    weekly = [{"date": d.isoformat(), "total": str(by_date.get(d.isoformat(), Decimal(0)))} for d in days]
    today_sales = by_date.get(today.isoformat(), Decimal(0))

    return {
        "currency": "EGP",
        "sales": {
            "orders_by_status": _count_by(Order.status),
            "realized_revenue": str(_sum(Order.total_cash, Order.status.in_(realized))),
            "today": str(today_sales),
            "open_orders": int(open_orders),
            "weekly": weekly,
        },
        "collection": {
            "dues_by_status": _count_by(CustomerDue.status),
            "outstanding": str(_sum(CustomerDue.amount, CustomerDue.status == "open")),
            "defaulted": str(_sum(CustomerDue.amount, CustomerDue.status == "defaulted")),
            "overdue": str(_sum(CustomerDue.amount, CustomerDue.status == "overdue")),
        },
        "credit": {"tier_distribution": _count_by(CustomerCreditTier.tier)},
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

"""Low-stock detection + escalation chain (US-4.3).

`check` scans stock balances at or below their reorder point and opens a
ReorderAlert at escalation level 1. The escalation ladder
(customer → branch/agent → company → supplier) advances via scheduled
re-checks in a later phase; v1 records the alert so the Notification
Center can fan it out.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ...common.money import to_money
from ...extensions import db
from ..models import ReorderAlert, StockBalance


def check(*, supplier_id: int | None = None) -> list[ReorderAlert]:
    """Open level-1 alerts for any balance at/under its reorder point that
    doesn't already have an unacknowledged alert. Returns the new alerts."""
    stmt = select(StockBalance).where(StockBalance.reorder_point.is_not(None))
    if supplier_id is not None:
        stmt = stmt.where(StockBalance.supplier_id == supplier_id)
    balances = db.session.execute(stmt).scalars().all()

    created: list[ReorderAlert] = []
    for bal in balances:
        if bal.reorder_point is None:
            continue
        if to_money(bal.on_hand) > to_money(bal.reorder_point):
            continue
        # Skip if an open (unacknowledged) alert already exists.
        existing = db.session.execute(
            select(ReorderAlert).where(
                ReorderAlert.stock_balance_id == bal.id,
                ReorderAlert.acknowledged_at.is_(None),
            )
        ).first()
        if existing is not None:
            continue
        alert = ReorderAlert(
            stock_balance_id=bal.id,
            level=1,
            payload_json={
                "product_id": bal.product_id,
                "supplier_id": bal.supplier_id,
                "on_hand": str(to_money(bal.on_hand)),
                "reorder_point": str(to_money(bal.reorder_point)),
            },
        )
        db.session.add(alert)
        created.append(alert)
    db.session.commit()
    return created


def serialize(alert: ReorderAlert) -> dict[str, Any]:
    return {
        "id": alert.id,
        "stock_balance_id": alert.stock_balance_id,
        "level": alert.level,
        "payload": alert.payload_json,
        "acknowledged_at": alert.acknowledged_at.isoformat()
        if alert.acknowledged_at
        else None,
    }

"""Low-stock detection + escalation chain (US-4.3).

`check` scans stock balances at or below their reorder point and opens a
ReorderAlert at escalation level 1. The escalation ladder
(customer → branch/agent → company → supplier) advances via scheduled
re-checks in a later phase; v1 records the alert so the Notification
Center can fan it out.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from ...common.errors import Conflict, NotFound
from ...common.money import to_money
from ...extensions import db
from ...settings import service as settings
from ..models import ReorderAlert, StockBalance

# Hours an alert may sit at a level before it climbs the chain (docs/EPIC 4) is
# tunable in «إعدادات النظام» (T-37), key `inventory.reorder_escalate_after_hours`.
# Top of the chain: level 4 = the supplier (restock request).
MAX_LEVEL = 4


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


def _notify_restock(bal: StockBalance) -> None:
    """Fan a level-4 alert out to the supplier as a restock request (US-4.3)."""
    from ...notifications.services import notify as notify_svc

    notify_svc.notify(
        user_id=bal.supplier_id,
        title="طلب إعادة توريد",
        body=f"المنتج #{bal.product_id} وصل حدّ إعادة الطلب في أحد المواقع — يرجى إعادة التوريد.",
        type_="reorder",
        channel="in_app",
    )


def escalate(*, min_hours_at_level: int | None = None) -> dict[str, int]:
    """Advance the reorder chain (docs/EPIC 4): an open alert at level < 4 whose
    stock is still low and has sat at its level ≥ min_hours climbs one level
    (1 customer/branch → 2 agent → 3 company → 4 supplier). A recovered balance
    closes its alert. Level 4 notifies the supplier. Run on a schedule. When
    `min_hours_at_level` is omitted the tunable default (T-37) applies."""
    hours = (
        min_hours_at_level
        if min_hours_at_level is not None
        else settings.get_int("inventory.reorder_escalate_after_hours")
    )
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=hours)
    open_alerts = db.session.execute(
        select(ReorderAlert).where(ReorderAlert.acknowledged_at.is_(None))
    ).scalars().all()

    reached_supplier: list[StockBalance] = []
    advanced = closed = 0
    for a in open_alerts:
        bal = db.session.get(StockBalance, a.stock_balance_id)
        if bal is None:
            continue
        still_low = (
            bal.reorder_point is not None
            and to_money(bal.on_hand) <= to_money(bal.reorder_point)
        )
        if not still_low:
            a.acknowledged_at = now  # restocked → auto-close
            closed += 1
            continue
        if a.level < MAX_LEVEL and a.triggered_at <= cutoff:
            a.level += 1
            a.triggered_at = now
            advanced += 1
            if a.level == MAX_LEVEL:
                reached_supplier.append(bal)
    db.session.commit()
    for bal in reached_supplier:
        _notify_restock(bal)
    return {"advanced": advanced, "closed": closed}


def scan(*, supplier_id: int | None = None) -> dict[str, int]:
    """One scheduled sweep: open new level-1 alerts, then advance the chain."""
    opened = len(check(supplier_id=supplier_id))
    result = escalate()
    return {"opened": opened, **result}


def acknowledge(*, alert_id: int, user_id: int) -> ReorderAlert:
    alert = db.session.get(ReorderAlert, alert_id)
    if alert is None:
        raise NotFound("التنبيه غير موجود", code="alert_not_found")
    if alert.acknowledged_at is not None:
        raise Conflict("التنبيه مُعالَج بالفعل", code="alert_already_acked")
    alert.acknowledged_at = datetime.now(UTC)
    alert.acknowledged_by = user_id
    db.session.commit()
    return alert


def list_alerts(*, open_only: bool = True) -> list[ReorderAlert]:
    stmt = select(ReorderAlert).order_by(ReorderAlert.level.desc(), ReorderAlert.id.desc())
    if open_only:
        stmt = stmt.where(ReorderAlert.acknowledged_at.is_(None))
    return list(db.session.execute(stmt).scalars())


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

"""Notification creation, delivery (stub channels), and reads."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, update

from ...common.errors import BadRequest, NotFound
from ...extensions import db
from ..models import CHANNELS, Notification


def _dispatch(n: Notification) -> None:
    """Deliver a notification on its channel. in_app is the stored row itself;
    the external channels are no-op stubs in this version (ready for a real
    SMS/WhatsApp/e-mail provider without an API change)."""
    if n.channel == "in_app":
        return
    # Placeholder: a real provider (Twilio, WhatsApp Cloud, SMTP) hooks here.
    return


def notify(
    *, user_id: int, title: str, body: str | None = None, type_: str = "system", channel: str = "in_app"
) -> Notification:
    if channel not in CHANNELS:
        raise BadRequest("قناة غير صالحة", code="bad_channel")
    n = Notification(user_id=user_id, type=type_, title=title, body=body, channel=channel)
    db.session.add(n)
    db.session.flush()
    _dispatch(n)
    db.session.commit()
    return n


def list_for(user_id: int, *, unread_only: bool = False, limit: int = 100) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.id.desc())
        .limit(limit)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    return list(db.session.execute(stmt).scalars())


def unread_count(user_id: int) -> int:
    return int(
        db.session.execute(
            select(db.func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        ).scalar_one()
    )


def mark_read(*, notification_id: int, user_id: int) -> Notification:
    n = db.session.get(Notification, notification_id)
    if n is None or n.user_id != user_id:
        raise NotFound("الإشعار غير موجود", code="notification_not_found")
    n.is_read = True
    db.session.commit()
    return n


def mark_all_read(user_id: int) -> int:
    result = db.session.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.session.commit()
    return int(result.rowcount or 0)


def serialize(n: Notification) -> dict[str, Any]:
    return {
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "channel": n.channel,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat(),
    }

"""Notification creation, external delivery, and reads."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, update

from ...common.errors import BadRequest, NotFound
from ...extensions import db
from ...identity.models import User
from ..models import CHANNELS, Notification
from ..providers.delivery import deliver

log = logging.getLogger(__name__)


def _dispatch(n: Notification) -> None:
    """Deliver a notification on its channel. `in_app` is the stored row itself;
    the external channels (sms/whatsapp/email) go through the delivery provider,
    which sends for real when configured and otherwise no-ops. Delivery failures
    are swallowed so they never roll back the notification."""
    if n.channel == "in_app":
        return
    user = db.session.get(User, n.user_id)
    if user is None:
        return
    target = user.phone if n.channel in ("sms", "whatsapp") else user.email
    try:
        deliver(channel=n.channel, target=target, title=n.title, body=n.body)
    except Exception:  # pragma: no cover - deliver already guards, belt & suspenders
        log.exception("notification dispatch failed (id=%s, channel=%s)", n.id, n.channel)


def redispatch(notification_id: int) -> bool:
    """Re-attempt delivery of an existing notification (the async Celery path).
    Returns True if the notification exists."""
    n = db.session.get(Notification, notification_id)
    if n is None:
        return False
    _dispatch(n)
    return True


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

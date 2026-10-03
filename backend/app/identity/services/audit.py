"""Audit event emitter.

Every sensitive mutation calls `emit()` with the dotted action name. The
`@audited` decorator wraps route handlers so forgetting to log is harder.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import g, request
from flask_jwt_extended import get_jwt_identity

from ...audit.models import AuditEvent
from ...extensions import db


def emit(
    action: str,
    *,
    actor_user_id: int | None = None,
    target_type: str | None = None,
    target_id: str | int | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
) -> AuditEvent:
    """Record one audit event. Caller commits."""

    if actor_user_id is None:
        try:
            raw = get_jwt_identity()
            actor_user_id = int(raw) if raw is not None else None
        except RuntimeError:
            actor_user_id = None

    ip, ua = _request_meta()
    event = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        before_json=before,
        after_json=after,
        reason=reason,
        ip=ip,
        user_agent=ua,
    )
    db.session.add(event)
    db.session.flush()
    return event


def audited(
    action: str, *, target_type: str | None = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that emits an audit event once the wrapped handler returns.

    The handler may set `g.audit_payload = {...}` to attach before/after
    snapshots or a reason. If the handler raises, no event is emitted.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = fn(*args, **kwargs)
            payload: dict[str, Any] = getattr(g, "audit_payload", {}) or {}
            emit(
                action,
                target_type=target_type or payload.get("target_type"),
                target_id=payload.get("target_id"),
                before=payload.get("before"),
                after=payload.get("after"),
                reason=payload.get("reason"),
            )
            return result

        return wrapper

    return decorator


def _request_meta() -> tuple[str | None, str | None]:
    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        ua = request.headers.get("User-Agent")
        return (ip, ua)
    except RuntimeError:
        # Outside request context (CLI, Celery).
        return (None, None)

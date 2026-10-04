"""/notifications blueprint — own inbox + admin send."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError

from ..common.errors import ApiError, BadRequest, Unauthorized
from ..identity.services.rbac import require_permission
from .schemas import SendNotificationIn
from .services import notify as svc

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


def _uid() -> int:
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    return int(raw)


@bp.get("")
@jwt_required()
def list_mine():
    unread = request.args.get("unread", "").lower() == "true"
    uid = _uid()
    items = svc.list_for(uid, unread_only=unread)
    return jsonify({"items": [svc.serialize(n) for n in items], "unread": svc.unread_count(uid)})


@bp.post("/<int:notification_id>/read")
@jwt_required()
def read_one(notification_id: int):
    n = svc.mark_read(notification_id=notification_id, user_id=_uid())
    return jsonify(svc.serialize(n))


@bp.post("/read-all")
@jwt_required()
def read_all():
    return jsonify({"marked": svc.mark_all_read(_uid())})


@bp.post("")
@require_permission("notify.send")
def send():
    body: Any = request.get_json(silent=True) or {}
    try:
        p = SendNotificationIn.model_validate(body)
    except ValidationError as e:
        raise BadRequest(f"Invalid payload: {e.errors()[0]['msg']}", code="validation_error") from e
    n = svc.notify(user_id=p.user_id, title=p.title, body=p.body, type_=p.type, channel=p.channel)
    return jsonify(svc.serialize(n)), 201


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

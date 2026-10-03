"""/comm blueprint — mediated chat (EPIC 10).

Conversations are created by a moderator (`comm.moderate`); messaging within
one is open to its two participants (and a moderator). Reading all
conversations / flagged messages is a moderator capability (US-10.3).
"""

from __future__ import annotations

import base64
import binascii
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError

from ..common.errors import ApiError, BadRequest, Unauthorized
from ..identity.services.rbac import has_permission, require_permission
from .schemas import SendMessageIn, StartConversationIn
from .services import chat as svc

bp = Blueprint("comm", __name__, url_prefix="/comm")


def _parse(model_cls: Any) -> Any:
    try:
        return model_cls.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        raise BadRequest(f"Invalid payload: {e.errors()[0]['msg']}", code="validation_error") from e


def _uid() -> int:
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    return int(raw)


def _is_mod() -> bool:
    return has_permission(_uid(), "comm.moderate")


@bp.post("/conversations")
@require_permission("comm.moderate")
def start_conversation():
    p = _parse(StartConversationIn)
    conv = svc.start_conversation(
        customer_id=p.customer_id, supplier_id=p.supplier_id, order_id=p.order_id, subject=p.subject
    )
    return jsonify(svc.serialize_conversation(conv, viewer_id=_uid(), is_admin=True)), 201


@bp.get("/conversations")
@jwt_required()
def list_conversations():
    uid = _uid()
    is_mod = _is_mod()
    status = request.args.get("status")
    flagged = request.args.get("flagged", "").lower() == "true"
    convs = svc.list_conversations(is_admin=is_mod, viewer_id=uid, status=status, flagged_only=flagged)
    return jsonify({"items": [svc.serialize_conversation(c, viewer_id=uid, is_admin=is_mod) for c in convs]})


@bp.get("/conversations/<int:conversation_id>/messages")
@jwt_required()
def list_messages(conversation_id: int):
    uid = _uid()
    is_mod = _is_mod()
    msgs = svc.list_messages(conversation_id=conversation_id, viewer_id=uid, is_admin=is_mod)
    return jsonify({"items": [svc.serialize_message(m, viewer_id=uid, is_admin=is_mod) for m in msgs]})


@bp.post("/conversations/<int:conversation_id>/messages")
@jwt_required()
def send_message(conversation_id: int):
    p = _parse(SendMessageIn)
    uid = _uid()
    image_bytes: bytes | None = None
    if p.image_b64:
        try:
            image_bytes = base64.b64decode(p.image_b64, validate=True)
        except (binascii.Error, ValueError) as e:
            raise BadRequest("صورة غير صالحة", code="bad_image") from e
    msg = svc.send_message(
        conversation_id=conversation_id,
        sender_id=uid,
        is_admin=_is_mod(),
        body=p.body,
        image_bytes=image_bytes,
    )
    return jsonify(svc.serialize_message(msg, viewer_id=uid, is_admin=_is_mod())), 201


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

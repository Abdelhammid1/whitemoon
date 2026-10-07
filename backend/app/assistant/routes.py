"""/assistant blueprint — admin-only AI knowledge assistant (read-only).

Every route is gated by the `assistant.use` permission (admin only; admin.high
via `*`), enforced in the backend — not just hidden in the UI (ticket §3/§25).
There are NO write endpoints into the business domain and no operational-DB
access: the assistant can only read its own knowledge base and answer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask_jwt_extended import get_jwt_identity
from pydantic import ValidationError

from ..common.errors import ApiError, BadRequest, Forbidden, NotFound, Unauthorized
from ..extensions import db
from ..identity.services.audit import emit as audit_emit
from ..identity.services.rbac import require_permission
from .models import AsstConversation, AsstMessage, KnowledgeGap, UsageCounter
from .providers import deepseek
from .schemas import AnswerGapIn, AskIn, NewConversationIn
from .services import chat, ocr, redaction, retrieval

bp = Blueprint("assistant", __name__, url_prefix="/assistant")


def _uid() -> int:
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    return int(raw)


def _parse(model_cls: Any) -> Any:
    try:
        return model_cls.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        raise BadRequest(f"Invalid payload: {e.errors()[0]['msg']}", code="validation_error") from e


def _own_conversation(conversation_id: int, uid: int) -> AsstConversation:
    conv = db.session.get(AsstConversation, conversation_id)
    if conv is None:
        raise NotFound("المحادثة غير موجودة", code="conversation_not_found")
    if conv.user_id != uid:
        raise Forbidden("ليست محادثتك", code="forbidden")
    return conv


# ---------------------------------------------------------------- conversations


@bp.post("/conversations")
@require_permission("assistant.use")
def create_conversation():
    p = _parse(NewConversationIn)
    conv = AsstConversation(user_id=_uid(), title=p.title)
    db.session.add(conv)
    db.session.commit()
    return jsonify({"id": conv.id, "title": conv.title}), 201


@bp.get("/conversations")
@require_permission("assistant.use")
def list_conversations():
    uid = _uid()
    rows = db.session.execute(
        db.select(AsstConversation)
        .where(AsstConversation.user_id == uid)
        .order_by(AsstConversation.id.desc())
        .limit(50)
    ).scalars().all()
    return jsonify({"items": [{"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat()} for c in rows]})


@bp.get("/conversations/<int:conversation_id>")
@require_permission("assistant.use")
def get_conversation(conversation_id: int):
    conv = _own_conversation(conversation_id, _uid())
    msgs = db.session.execute(
        db.select(AsstMessage).where(AsstMessage.conversation_id == conv.id).order_by(AsstMessage.id)
    ).scalars().all()
    return jsonify(
        {
            "id": conv.id,
            "title": conv.title,
            "messages": [
                {"role": m.role, "content": m.content, "meta": m.meta, "created_at": m.created_at.isoformat()}
                for m in msgs
            ],
        }
    )


@bp.post("/conversations/<int:conversation_id>/ask")
@require_permission("assistant.use")
def ask(conversation_id: int):
    uid = _uid()
    _own_conversation(conversation_id, uid)  # ownership check (within this session)
    p = _parse(AskIn)
    # Pass the id as a plain value — never the ORM object — into the streaming
    # generator. The generator runs after this handler returns and manages its
    # own session; a detached/expired instance would raise DetachedInstanceError
    # (titling + committing here previously expired `conv`).
    gen = chat.answer(conversation_id, p.question, route=p.route, actor_id=uid)
    return Response(
        stream_with_context(gen),
        mimetype="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------- uploads (OCR)


@bp.post("/upload")
@require_permission("assistant.use")
def upload():
    """Extract text from a screenshot/PDF locally, redact it, and return only the
    cleaned text (the original file never leaves the server — ticket §13)."""
    f = request.files.get("file")
    if f is None or not f.filename:
        raise BadRequest("مطلوب ملف", code="file_required")
    data = f.read(12 * 1024 * 1024 + 1)
    if len(data) > 12 * 1024 * 1024:
        raise BadRequest("حجم الملف كبير جدًا", code="file_too_large")
    try:
        text = ocr.extract_text(data, filename=f.filename)
    except ocr.OcrUnavailable as e:
        raise BadRequest(str(e), code="ocr_unavailable") from e
    clean = redaction.redact(text)
    redaction.log_findings("ocr", clean.findings)
    db.session.commit()
    audit_emit("assistant.upload", actor_user_id=_uid(), target_type="assistant_upload", target_id=0)
    return jsonify({"text": clean.text, "redaction": clean.findings})


# ---------------------------------------------------------------- status


@bp.get("/status")
@require_permission("assistant.use")
def status():
    from .models import IndexVersion

    uid = _uid()
    iv = db.session.execute(
        db.select(IndexVersion).where(IndexVersion.status == "ready").order_by(IndexVersion.version.desc()).limit(1)
    ).scalar_one_or_none()
    today = datetime.now(UTC).date()
    usage = db.session.execute(
        db.select(UsageCounter).where(UsageCounter.day == today, UsageCounter.user_id == uid)
    ).scalar_one_or_none()
    return jsonify(
        {
            "index": {
                "version": iv.version if iv else None,
                "ready": iv is not None,
                "degraded": bool(iv.degraded) if iv else None,
                "doc_count": iv.doc_count if iv else 0,
                "chunk_count": iv.chunk_count if iv else 0,
                "indexed_at": iv.finished_at.isoformat() if iv and iv.finished_at else None,
            },
            "deepseek": deepseek.health(),
            "usage": {
                "messages_today": usage.message_count if usage else 0,
                "daily_cap": chat.DAILY_MESSAGE_CAP,
            },
            "retrieval_available": retrieval.current_version() is not None,
        }
    )


# ---------------------------------------------------------------- knowledge gaps


@bp.get("/gaps")
@require_permission("assistant.use")
def list_gaps():
    status_filter = request.args.get("status", "open")
    rows = db.session.execute(
        db.select(KnowledgeGap).where(KnowledgeGap.status == status_filter).order_by(KnowledgeGap.id.desc()).limit(200)
    ).scalars().all()
    return jsonify(
        {
            "items": [
                {
                    "id": g.id,
                    "question": g.question,
                    "route": g.route,
                    "status": g.status,
                    "answer": g.answer,
                    "created_at": g.created_at.isoformat(),
                }
                for g in rows
            ]
        }
    )


@bp.post("/gaps/<int:gap_id>/answer")
@require_permission("assistant.use")
def answer_gap(gap_id: int):
    p = _parse(AnswerGapIn)
    gap = db.session.get(KnowledgeGap, gap_id)
    if gap is None:
        raise NotFound("غير موجود", code="gap_not_found")
    gap.answer = p.answer
    gap.status = "answered"
    gap.answered_by = _uid()
    gap.answered_at = datetime.now(UTC)
    audit_emit("assistant.gap.answer", actor_user_id=_uid(), target_type="knowledge_gap", target_id=gap.id)
    db.session.commit()
    return jsonify({"id": gap.id, "status": gap.status})


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status

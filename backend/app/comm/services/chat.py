"""Mediated chat — EPIC 10.

Messages always pass through here (no peer-to-peer). Each message is scanned
for contact-exchange and either delivered (`sent`) or withheld (`blocked`)
while still being retained for admin oversight. Serialization never reveals
the counterpart's identity to a participant (US-10.1).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ...common.errors import BadRequest, Forbidden, NotFound
from ...extensions import db
from ...identity.services.audit import emit as audit_emit
from ..models import Conversation, Message
from . import filters


def start_conversation(
    *, customer_id: int, supplier_id: int, order_id: int | None = None, subject: str | None = None
) -> Conversation:
    if customer_id == supplier_id:
        raise BadRequest("طرفا المحادثة متطابقان", code="same_party")
    conv = Conversation(
        customer_id=customer_id,
        supplier_id=supplier_id,
        order_id=order_id,
        subject=subject,
        status="open",
    )
    db.session.add(conv)
    db.session.commit()
    return conv


def _conversation_or_404(conversation_id: int) -> Conversation:
    conv = db.session.get(Conversation, conversation_id)
    if conv is None:
        raise NotFound("المحادثة غير موجودة", code="conversation_not_found")
    return conv


def role_of(conv: Conversation, user_id: int, *, is_admin: bool) -> str | None:
    if user_id == conv.customer_id:
        return "customer"
    if user_id == conv.supplier_id:
        return "supplier"
    if is_admin:
        return "admin"
    return None


def send_message(
    *,
    conversation_id: int,
    sender_id: int,
    is_admin: bool = False,
    body: str | None = None,
    image_bytes: bytes | None = None,
    image_url: str | None = None,
) -> Message:
    """Post a message through the mediator. If it carries contact info it is
    stored as `blocked` and not delivered, but kept for oversight."""
    conv = _conversation_or_404(conversation_id)
    role = role_of(conv, sender_id, is_admin=is_admin)
    if role is None:
        raise Forbidden("لست طرفًا في هذه المحادثة", code="not_participant")
    if conv.status != "open":
        raise BadRequest("المحادثة مغلقة", code="conversation_closed")
    if not body and not image_url and not image_bytes:
        raise BadRequest("الرسالة فارغة", code="empty_message")

    reason = filters.scan_message(body=body, image_bytes=image_bytes)
    status = "blocked" if reason is not None else "sent"

    msg = Message(
        conversation_id=conv.id,
        sender_id=sender_id,
        sender_role=role,
        body=body,
        image_url=image_url,
        status=status,
        block_reason=reason,
    )
    db.session.add(msg)
    if reason is not None:
        # Record the blocked attempt for admin oversight (US-10.3).
        db.session.flush()
        audit_emit("comm.message.blocked", actor_user_id=sender_id, target_type="message", target_id=msg.id, reason=reason)
    db.session.commit()
    return msg


def list_messages(*, conversation_id: int, viewer_id: int, is_admin: bool) -> list[Message]:
    conv = _conversation_or_404(conversation_id)
    role = role_of(conv, viewer_id, is_admin=is_admin)
    if role is None:
        raise Forbidden("لست طرفًا في هذه المحادثة", code="not_participant")
    rows = list(
        db.session.execute(
            select(Message).where(Message.conversation_id == conv.id).order_by(Message.id)
        ).scalars()
    )
    if is_admin:
        return rows
    # A participant sees delivered messages plus their own (incl. blocked);
    # a blocked message is never shown to the other party.
    return [m for m in rows if m.status == "sent" or m.sender_id == viewer_id]


def list_conversations(
    *,
    is_admin: bool,
    viewer_id: int,
    status: str | None = None,
    flagged_only: bool = False,
) -> list[Conversation]:
    stmt = select(Conversation).order_by(Conversation.id.desc())
    if not is_admin:
        stmt = stmt.where(
            (Conversation.customer_id == viewer_id) | (Conversation.supplier_id == viewer_id)
        )
    if status:
        stmt = stmt.where(Conversation.status == status)
    convs = list(db.session.execute(stmt).scalars())
    if flagged_only:
        convs = [c for c in convs if any(m.status == "blocked" for m in c.messages)]
    return convs


def serialize_message(m: Message, *, viewer_id: int, is_admin: bool) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "sender_role": m.sender_role,
        "mine": m.sender_id == viewer_id,
        "body": m.body,
        "image_url": m.image_url,
        "status": m.status,
        "created_at": m.created_at.isoformat(),
    }
    if m.status == "blocked":
        out["block_reason"] = m.block_reason
    # The counterpart's user id is revealed only to an admin (US-10.1).
    if is_admin:
        out["sender_id"] = m.sender_id
    return out


def serialize_conversation(c: Conversation, *, viewer_id: int, is_admin: bool) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": c.id,
        "order_id": c.order_id,
        "subject": c.subject,
        "status": c.status,
    }
    if is_admin:
        out["customer_id"] = c.customer_id
        out["supplier_id"] = c.supplier_id
        out["flagged"] = any(m.status == "blocked" for m in c.messages)
    else:
        # Identity isolation: a participant sees only who the *other* side is
        # by role, never their id.
        out["counterpart_role"] = "supplier" if viewer_id == c.customer_id else "customer"
    return out

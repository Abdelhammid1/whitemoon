"""Mediated conversations & messages — EPIC 10.

Schema `comm`. Every message is stored server-side (no peer-to-peer). A
message that fails the contact-exchange filter is stored with
`status='blocked'` and never delivered to the other party, but is retained
for admin oversight (US-10.2/10.3).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..common.base_model import Base, TimestampMixin

CONVERSATION_STATUSES = ("open", "closed")
MESSAGE_STATUSES = ("sent", "blocked")
SENDER_ROLES = ("customer", "supplier", "admin")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("status in ('open','closed')", name="ck_conversations_status"),
        Index("ix_conversations_customer", "customer_id"),
        Index("ix_conversations_supplier", "supplier_id"),
        {"schema": "comm"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int | None] = mapped_column(BigInteger)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="open")
    subject: Mapped[str | None] = mapped_column(String(200))

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("status in ('sent','blocked')", name="ck_messages_status"),
        CheckConstraint(
            "sender_role in ('customer','supplier','admin')", name="ck_messages_sender_role"
        ),
        Index("ix_messages_conversation", "conversation_id"),
        Index("ix_messages_status", "status"),
        {"schema": "comm"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("comm.conversations.id"), nullable=False
    )
    sender_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    sender_role: Mapped[str] = mapped_column(String(10), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="sent")
    block_reason: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

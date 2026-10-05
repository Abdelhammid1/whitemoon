"""Notification store — schema `notifications`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..common.base_model import Base

CHANNELS = ("in_app", "sms", "whatsapp", "email")
# Arabic labels — single source for the UI (served by GET /notifications/channels).
CHANNEL_LABELS = {
    "in_app": "داخل التطبيق",
    "sms": "رسالة نصية",
    "whatsapp": "واتساب",
    "email": "بريد إلكتروني",
}


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "channel in ('in_app','sms','whatsapp','email')", name="ck_notifications_channel"
        ),
        Index("ix_notifications_user", "user_id", "is_read"),
        {"schema": "notifications"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False, default="system")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(10), nullable=False, default="in_app")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

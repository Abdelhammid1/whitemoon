"""Request bodies for /notifications."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SendNotificationIn(BaseModel):
    user_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    body: str | None = Field(default=None, max_length=4000)
    type: str = Field(default="system", max_length=40)
    channel: str = Field(default="in_app", pattern="^(in_app|sms|whatsapp|email)$")

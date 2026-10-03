"""Request bodies for the /comm blueprint (EPIC 10)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StartConversationIn(BaseModel):
    customer_id: int = Field(gt=0)
    supplier_id: int = Field(gt=0)
    order_id: int | None = None
    subject: str | None = Field(default=None, max_length=200)


class SendMessageIn(BaseModel):
    body: str | None = Field(default=None, max_length=4000)
    image_url: str | None = Field(default=None, max_length=500)
    # Optional base64 image content, scanned by OCR for hidden phone numbers.
    image_b64: str | None = None

"""Request bodies for the /compliance blueprint (EPIC 11)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SetEtaIn(BaseModel):
    eta_code: str | None = Field(default=None, max_length=60)
    eta_ready: bool = False

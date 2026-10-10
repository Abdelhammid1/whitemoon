"""System-settings storage (T-37) — overrides + an append-only change log.

A `SystemSetting` row exists only for a key an admin has overridden; otherwise
the registry default applies. Every write appends a `SystemSettingChange`.
Both live in the `identity` schema (admin-owned, like audit).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..common.base_model import Base, TimestampMixin


class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"
    __table_args__ = ({"schema": "identity"},)

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=True
    )


class SystemSettingChange(Base):
    __tablename__ = "system_setting_changes"
    __table_args__ = (
        Index("ix_identity_system_setting_changes_key", "key"),
        {"schema": "identity"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

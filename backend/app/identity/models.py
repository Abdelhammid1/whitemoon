"""Identity, authn/authz, 2FA, impersonation.

Mirrors docs/01-db-schema-skeleton.md § identity.

Design rules enforced here:
- Password is stored only as an Argon2 hash (US-0.1).
- `kind` discriminates customer / supplier / channel partner / staff / admin.
- Supplier accounts start `pending` and are not activated by OTP alone — admin
  must approve them (US-1.3 / US-0.1).
- OTP codes are stored as HMAC hashes, not plaintext.
- `audit.events` holds a full trail per US-0.2.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..common.base_model import Base, TimestampMixin

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------- enums (as str)

USER_KINDS = ("customer", "supplier", "agent", "branch", "staff", "admin")
USER_STATUSES = ("pending", "active", "suspended", "locked")
LOCALES = ("ar", "en")
OTP_CHANNELS = ("sms", "whatsapp", "email")
PARTNER_TYPES = ("agent", "branch")
APPROVAL_STATUSES = ("pending", "approved", "rejected")


# ---------------------------------------------------------------- core user


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_users_phone"),
        UniqueConstraint("email", name="uq_users_email"),
        {"schema": "identity"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    locale: Mapped[str] = mapped_column(String(5), nullable=False, default="ar")

    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[str | None] = mapped_column(String(45))

    user_roles: Mapped[list[UserRole]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    supplier_profile: Mapped[SupplierProfile | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="SupplierProfile.user_id",
    )
    customer_profile: Mapped[CustomerProfile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    partner_profile: Mapped[ChannelPartnerProfile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    totp_secret: Mapped[TotpSecret | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------- profiles


class SupplierProfile(Base, TimestampMixin):
    __tablename__ = "supplier_profiles"
    __table_args__ = {"schema": "identity"}

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), primary_key=True
    )
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    commercial_register_no: Mapped[str] = mapped_column(String(60), nullable=False)
    tax_card_no: Mapped[str] = mapped_column(String(60), nullable=False)
    national_id: Mapped[str] = mapped_column(String(60), nullable=False)
    # Minimum order value per supplier (T-03, US-4.5): a sub-order below this
    # is blocked at checkout. 0 = no minimum.
    min_order_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0, server_default="0"
    )
    approval_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    approved_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("identity.users.id")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(String(1000))

    user: Mapped[User] = relationship(
        back_populates="supplier_profile", foreign_keys=[user_id]
    )


class CustomerProfile(Base, TimestampMixin):
    __tablename__ = "customer_profiles"
    __table_args__ = {"schema": "identity"}

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    default_shipping_address_id: Mapped[int | None] = mapped_column(BigInteger)
    # Geographic area (governorate/region) used to scope agent/branch access
    # to their assigned territory (T-01, US-1.8).
    geo_area: Mapped[str | None] = mapped_column(String(200))

    user: Mapped[User] = relationship(back_populates="customer_profile")


class ChannelPartnerProfile(Base, TimestampMixin):
    """Unified table for agents AND branches per US-6 implementation note.

    `type` discriminates. Agents see commission + investment-return screens;
    branches do not.
    """

    __tablename__ = "channel_partner_profiles"
    __table_args__ = {"schema": "identity"}

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), primary_key=True
    )
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    geo_scope: Mapped[str | None] = mapped_column(String(200))
    commission_rate_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    deposit_amount: Mapped[float | None] = mapped_column(Numeric(18, 4))

    user: Mapped[User] = relationship(back_populates="partner_profile")


# ---------------------------------------------------------------- RBAC


class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("code", name="uq_roles_code"),
        {"schema": "identity"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_permissions_code"),
        {"schema": "identity"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    description_ar: Mapped[str] = mapped_column(String(300), nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = {"schema": "identity"}

    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.roles.id"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.permissions.id"), primary_key=True
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = {"schema": "identity"}

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.roles.id"), primary_key=True
    )

    user: Mapped[User] = relationship(back_populates="user_roles")
    role: Mapped[Role] = relationship()


# ---------------------------------------------------------------- OTP + 2FA


class OtpRequest(Base):
    __tablename__ = "otp_requests"
    __table_args__ = (
        Index("ix_otp_requests_user_channel", "user_id", "channel"),
        {"schema": "identity"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("identity.users.id"))
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)  # register, login, reset
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TotpSecret(Base):
    __tablename__ = "totp_secrets"
    __table_args__ = {"schema": "identity"}

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), primary_key=True
    )
    secret: Mapped[str] = mapped_column(String(100), nullable=False)
    enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="totp_secret")


class BackupCode(Base):
    __tablename__ = "backup_codes"
    __table_args__ = (
        Index("ix_backup_codes_user", "user_id"),
        {"schema": "identity"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("identity.users.id"))
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------- sessions


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_jti", "jwt_jti"),
        {"schema": "identity"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("identity.users.id"))
    jwt_jti: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # access | refresh
    device: Mapped[str | None] = mapped_column(String(300))
    ip: Mapped[str | None] = mapped_column(String(45))
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImpersonationGrant(Base):
    """Who impersonated whom, when, why. Full audit per US-0.3."""

    __tablename__ = "impersonation_grants"
    __table_args__ = {"schema": "identity"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    admin_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("identity.users.id"))
    target_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("identity.users.id"))
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

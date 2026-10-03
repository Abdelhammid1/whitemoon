"""Baseline — identity and audit schemas.

Revision ID: 0001
Revises:
Create Date: 2026-10-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS identity")
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")

    # ----- identity.users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("locale", sa.String(length=5), nullable=False, server_default="ar"),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(length=45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint(
            "kind in ('customer','supplier','agent','branch','staff','admin')",
            name="ck_users_kind",
        ),
        sa.CheckConstraint(
            "status in ('pending','active','suspended','locked')",
            name="ck_users_status",
        ),
        sa.CheckConstraint("locale in ('ar','en')", name="ck_users_locale"),
        schema="identity",
    )

    # ----- identity.supplier_profiles
    op.create_table(
        "supplier_profiles",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            primary_key=True,
        ),
        sa.Column("legal_name", sa.String(length=200), nullable=False),
        sa.Column("commercial_register_no", sa.String(length=60), nullable=False),
        sa.Column("tax_card_no", sa.String(length=60), nullable=False),
        sa.Column("national_id", sa.String(length=60), nullable=False),
        sa.Column(
            "approval_status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "approved_by",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "approval_status in ('pending','approved','rejected')",
            name="ck_supplier_profiles_approval_status",
        ),
        schema="identity",
    )

    # ----- identity.customer_profiles
    op.create_table(
        "customer_profiles",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            primary_key=True,
        ),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("default_shipping_address_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="identity",
    )

    # ----- identity.channel_partner_profiles
    op.create_table(
        "channel_partner_profiles",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            primary_key=True,
        ),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("geo_scope", sa.String(length=200), nullable=True),
        sa.Column("commission_rate_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("deposit_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "type in ('agent','branch')",
            name="ck_channel_partner_profiles_type",
        ),
        schema="identity",
    )

    # ----- identity.roles
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name_ar", sa.String(length=100), nullable=False),
        sa.Column("name_en", sa.String(length=100), nullable=False),
        sa.Column(
            "is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("code", name="uq_roles_code"),
        schema="identity",
    )

    # ----- identity.permissions
    op.create_table(
        "permissions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description_ar", sa.String(length=300), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
        schema="identity",
    )

    # ----- identity.role_permissions
    op.create_table(
        "role_permissions",
        sa.Column(
            "role_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.roles.id"),
            primary_key=True,
        ),
        sa.Column(
            "permission_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.permissions.id"),
            primary_key=True,
        ),
        schema="identity",
    )

    # ----- identity.user_roles
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.roles.id"),
            primary_key=True,
        ),
        schema="identity",
    )

    # ----- identity.otp_requests
    op.create_table(
        "otp_requests",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False
        ),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "attempts", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "channel in ('sms','whatsapp','email')",
            name="ck_otp_requests_channel",
        ),
        schema="identity",
    )
    op.create_index(
        "ix_otp_requests_user_channel",
        "otp_requests",
        ["user_id", "channel"],
        schema="identity",
    )

    # ----- identity.totp_secrets
    op.create_table(
        "totp_secrets",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            primary_key=True,
        ),
        sa.Column("secret", sa.String(length=100), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        schema="identity",
    )

    # ----- identity.backup_codes
    op.create_table(
        "backup_codes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False
        ),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        schema="identity",
    )
    op.create_index(
        "ix_backup_codes_user", "backup_codes", ["user_id"], schema="identity"
    )

    # ----- identity.sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False
        ),
        sa.Column("jwt_jti", sa.String(length=60), nullable=False, unique=True),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("device", sa.String(length=300), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind in ('access','refresh')", name="ck_sessions_kind"
        ),
        schema="identity",
    )
    op.create_index(
        "ix_sessions_jti", "sessions", ["jwt_jti"], schema="identity"
    )

    # ----- identity.impersonation_grants
    op.create_table(
        "impersonation_grants",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "admin_user_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column(
            "target_user_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        schema="identity",
    )

    # ----- audit.events
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "actor_user_id",
            sa.BigInteger(),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=60), nullable=True),
        sa.Column("target_id", sa.String(length=60), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="audit",
    )
    op.create_index("ix_events_action", "events", ["action"], schema="audit")
    op.create_index("ix_events_at", "events", ["at"], schema="audit")


def downgrade() -> None:
    op.drop_index("ix_events_at", table_name="events", schema="audit")
    op.drop_index("ix_events_action", table_name="events", schema="audit")
    op.drop_table("events", schema="audit")

    op.drop_table("impersonation_grants", schema="identity")
    op.drop_index("ix_sessions_jti", table_name="sessions", schema="identity")
    op.drop_table("sessions", schema="identity")
    op.drop_index("ix_backup_codes_user", table_name="backup_codes", schema="identity")
    op.drop_table("backup_codes", schema="identity")
    op.drop_table("totp_secrets", schema="identity")
    op.drop_index(
        "ix_otp_requests_user_channel", table_name="otp_requests", schema="identity"
    )
    op.drop_table("otp_requests", schema="identity")
    op.drop_table("user_roles", schema="identity")
    op.drop_table("role_permissions", schema="identity")
    op.drop_table("permissions", schema="identity")
    op.drop_table("roles", schema="identity")
    op.drop_table("channel_partner_profiles", schema="identity")
    op.drop_table("customer_profiles", schema="identity")
    op.drop_table("supplier_profiles", schema="identity")
    op.drop_table("users", schema="identity")

    op.execute("DROP SCHEMA IF EXISTS audit")
    op.execute("DROP SCHEMA IF EXISTS identity")

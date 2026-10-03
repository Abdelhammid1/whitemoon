"""comm schema — conversations and messages (mediated chat).

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS comm")

    op.create_table(
        "conversations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("order_id", sa.BigInteger(), nullable=True),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("supplier_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default=sa.text("'open'")),
        sa.Column("subject", sa.String(200), nullable=True),
        *_ts(),
        sa.CheckConstraint("status in ('open','closed')", name="ck_conversations_status"),
        schema="comm",
    )
    op.create_index("ix_conversations_customer", "conversations", ["customer_id"], schema="comm")
    op.create_index("ix_conversations_supplier", "conversations", ["supplier_id"], schema="comm")

    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("conversation_id", sa.BigInteger(), sa.ForeignKey("comm.conversations.id"), nullable=False),
        sa.Column("sender_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("sender_role", sa.String(10), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default=sa.text("'sent'")),
        sa.Column("block_reason", sa.String(60), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status in ('sent','blocked')", name="ck_messages_status"),
        sa.CheckConstraint("sender_role in ('customer','supplier','admin')", name="ck_messages_sender_role"),
        schema="comm",
    )
    op.create_index("ix_messages_conversation", "messages", ["conversation_id"], schema="comm")
    op.create_index("ix_messages_status", "messages", ["status"], schema="comm")


def downgrade() -> None:
    op.drop_index("ix_messages_status", table_name="messages", schema="comm")
    op.drop_index("ix_messages_conversation", table_name="messages", schema="comm")
    op.drop_table("messages", schema="comm")
    op.drop_index("ix_conversations_supplier", table_name="conversations", schema="comm")
    op.drop_index("ix_conversations_customer", table_name="conversations", schema="comm")
    op.drop_table("conversations", schema="comm")
    op.execute("DROP SCHEMA IF EXISTS comm")

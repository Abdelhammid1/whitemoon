"""Admin AI Assistant — schema `assistant` + pgvector knowledge base.

Creates the `vector` extension, an isolated `assistant` schema (no FKs into
business schemas except identity.users for conversation ownership), the RAG
knowledge-base tables (kb_documents / kb_chunks with a 1024-dim embedding),
conversations/messages, knowledge gaps, index-version bookkeeping, a redaction
audit, and per-day usage counters.

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0026"
down_revision: str | Sequence[str] | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBED_DIM = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE SCHEMA IF NOT EXISTS assistant")

    op.create_table(
        "kb_documents",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source_path", sa.String(500), nullable=False),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("title", sa.String(300)),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("index_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "source_type in ('code','doc','guide','help','onboarding','faq','readme')",
            name="ck_kb_documents_source_type",
        ),
        schema="assistant",
    )
    op.create_index("ix_kb_documents_version", "kb_documents", ["index_version"], schema="assistant")
    op.create_index("ix_kb_documents_path", "kb_documents", ["source_path"], schema="assistant")

    op.create_table(
        "kb_chunks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("document_id", sa.BigInteger(), sa.ForeignKey("assistant.kb_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("index_version", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_path", sa.String(500), nullable=False),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("title", sa.String(300)),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", Vector(EMBED_DIM), nullable=False),
        schema="assistant",
    )
    op.create_index("ix_kb_chunks_document", "kb_chunks", ["document_id"], schema="assistant")
    op.create_index("ix_kb_chunks_version", "kb_chunks", ["index_version"], schema="assistant")
    # Approximate-NN index for cosine similarity retrieval.
    op.execute(
        "CREATE INDEX ix_kb_chunks_embedding ON assistant.kb_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "index_versions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, unique=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="running"),
        sa.Column("doc_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("degraded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("git_sha", sa.String(40)),
        sa.Column("notes", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status in ('running','ready','failed')", name="ck_index_versions_status"),
        schema="assistant",
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("title", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="assistant",
    )
    op.create_index("ix_asst_conversations_user", "conversations", ["user_id"], schema="assistant")

    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("conversation_id", sa.BigInteger(), sa.ForeignKey("assistant.conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role in ('user','assistant','system')", name="ck_asst_messages_role"),
        schema="assistant",
    )
    op.create_index("ix_asst_messages_conversation", "messages", ["conversation_id"], schema="assistant")

    op.create_table(
        "knowledge_gaps",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("conversation_id", sa.BigInteger()),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("context", sa.Text()),
        sa.Column("route", sa.String(300)),
        sa.Column("status", sa.String(10), nullable=False, server_default="open"),
        sa.Column("answer", sa.Text()),
        sa.Column("answered_by", sa.BigInteger()),
        sa.Column("answered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status in ('open','answered','dismissed')", name="ck_knowledge_gaps_status"),
        schema="assistant",
    )
    op.create_index("ix_knowledge_gaps_status", "knowledge_gaps", ["status"], schema="assistant")

    op.create_table(
        "redaction_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="assistant",
    )

    op.create_table(
        "usage_counters",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("day", "user_id", name="uq_usage_counters_day_user"),
        schema="assistant",
    )


def downgrade() -> None:
    for t in (
        "usage_counters",
        "redaction_log",
        "knowledge_gaps",
        "messages",
        "conversations",
        "index_versions",
        "kb_chunks",
        "kb_documents",
    ):
        op.drop_table(t, schema="assistant")
    op.execute("DROP SCHEMA IF EXISTS assistant CASCADE")

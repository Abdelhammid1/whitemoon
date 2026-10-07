"""Admin AI Assistant — data model (schema `assistant`).

Deliberately isolated from the business domains: nothing here references a
customer, order, invoice, product or any operational/financial table. The
assistant stores only its knowledge index (code/docs embeddings), its own
conversations, knowledge gaps, index-version bookkeeping, a redaction audit
(what was masked, never the value) and per-day usage counters.
"""

from __future__ import annotations

from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..common.base_model import Base, TimestampMixin

# bge-m3 produces 1024-dim embeddings; the deterministic dev fallback matches.
EMBED_DIM = 1024

KB_SOURCE_TYPES = ("code", "doc", "guide", "help", "onboarding", "faq", "readme")


class KbDocument(Base):
    """One indexed source (a file, a doc section, a page-help entry …)."""

    __tablename__ = "kb_documents"
    __table_args__ = (
        CheckConstraint(
            "source_type in ('code','doc','guide','help','onboarding','faq','readme')",
            name="ck_kb_documents_source_type",
        ),
        Index("ix_kb_documents_version", "index_version"),
        Index("ix_kb_documents_path", "source_path"),
        {"schema": "assistant"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str | None] = mapped_column(String(300))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    index_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    chunks: Mapped[list[KbChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class KbChunk(Base):
    """A retrievable passage with its embedding."""

    __tablename__ = "kb_chunks"
    __table_args__ = (
        Index("ix_kb_chunks_document", "document_id"),
        Index("ix_kb_chunks_version", "index_version"),
        {"schema": "assistant"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assistant.kb_documents.id", ondelete="CASCADE"), nullable=False
    )
    index_version: Mapped[int] = mapped_column(Integer, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str | None] = mapped_column(String(300))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM), nullable=False)
    document: Mapped[KbDocument] = relationship(back_populates="chunks")


class IndexVersion(Base):
    """Bookkeeping for each (re)index run — the version shown to the admin."""

    __tablename__ = "index_versions"
    __table_args__ = (
        CheckConstraint("status in ('running','ready','failed')", name="ck_index_versions_status"),
        {"schema": "assistant"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="running")
    doc_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    degraded: Mapped[bool] = mapped_column(nullable=False, default=False)
    git_sha: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AsstConversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_asst_conversations_user", "user_id"),
        {"schema": "assistant"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("identity.users.id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(300))
    messages: Mapped[list[AsstMessage]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="AsstMessage.id"
    )


class AsstMessage(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role in ('user','assistant','system')", name="ck_asst_messages_role"),
        Index("ix_asst_messages_conversation", "conversation_id"),
        {"schema": "assistant"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assistant.conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # route/page context, retrieval citations, redaction summary — never raw data.
    meta: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    conversation: Mapped[AsstConversation] = relationship(back_populates="messages")


class KnowledgeGap(Base):
    """A question the KB could not answer well — queued for a human to answer.
    Question/context are stored already redacted (the admin may paste data)."""

    __tablename__ = "knowledge_gaps"
    __table_args__ = (
        CheckConstraint("status in ('open','answered','dismissed')", name="ck_knowledge_gaps_status"),
        Index("ix_knowledge_gaps_status", "status"),
        {"schema": "assistant"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[int | None] = mapped_column(BigInteger)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text)
    route: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="open")
    answer: Mapped[str | None] = mapped_column(Text)
    answered_by: Mapped[int | None] = mapped_column(BigInteger)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )


class RedactionLog(Base):
    """What a redaction pass masked — kind + count only, never the value."""

    __tablename__ = "redaction_log"
    __table_args__ = ({"schema": "assistant"},)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)  # question|technical|ocr|gap
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )


class UsageCounter(Base):
    """Per-admin, per-day message + token counters for the daily cap."""

    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint("day", "user_id", name="uq_usage_counters_day_user"),
        {"schema": "assistant"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

"""Assistant knowledge-gap detection fields.

Store what the assistant replied, how the gap was detected (retrieval /
heuristic / judge / user_feedback) and a short reason — so answer-based and
LLM-judge detection and the 👎 feedback button can record richer gaps.

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: str | Sequence[str] | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("knowledge_gaps", sa.Column("assistant_answer", sa.Text()), schema="assistant")
    op.add_column("knowledge_gaps", sa.Column("source", sa.String(length=20)), schema="assistant")
    op.add_column("knowledge_gaps", sa.Column("detail", sa.Text()), schema="assistant")


def downgrade() -> None:
    op.drop_column("knowledge_gaps", "detail", schema="assistant")
    op.drop_column("knowledge_gaps", "source", schema="assistant")
    op.drop_column("knowledge_gaps", "assistant_answer", schema="assistant")

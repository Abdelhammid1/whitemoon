"""RAG retrieval (ticket §21) — pgvector cosine search over the current index."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from ...extensions import db
from ..models import IndexVersion, KbChunk
from ..providers import embeddings


@dataclass
class Hit:
    text: str
    source_path: str
    source_type: str
    title: str | None
    score: float  # cosine similarity in [−1, 1]; higher = closer


def current_version() -> int | None:
    """The newest index marked ready, or None when nothing is indexed yet."""
    return db.session.execute(
        select(IndexVersion.version)
        .where(IndexVersion.status == "ready")
        .order_by(IndexVersion.version.desc())
        .limit(1)
    ).scalar_one_or_none()


def retrieve(query: str, *, k: int = 6) -> list[Hit]:
    version = current_version()
    if version is None:
        return []
    qvec = embeddings.embed_query(query)
    distance = KbChunk.embedding.cosine_distance(qvec)
    rows = db.session.execute(
        select(
            KbChunk.text,
            KbChunk.source_path,
            KbChunk.source_type,
            KbChunk.title,
            distance.label("distance"),
        )
        .where(KbChunk.index_version == version)
        .order_by(distance)
        .limit(k)
    ).all()
    return [
        Hit(
            text=r.text,
            source_path=r.source_path,
            source_type=r.source_type,
            title=r.title,
            score=1.0 - float(r.distance),
        )
        for r in rows
    ]

"""Codebase + docs indexing pipeline (ticket §5/§6/§7/§10).

Walks the repository, excludes secret-bearing/irrelevant paths, runs a secret
pre-scan (gitleaks when available, else a regex guard) and skips any file that
trips it, then chunks → embeds (locally) → stores into a NEW index version.
Retrieval only ever reads the latest `ready` version, so a reindex is atomic
from the reader's point of view; older versions are pruned on success.

All of this runs inside our own server before anything is sent to DeepSeek.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, select

from ...extensions import db
from ..models import IndexVersion, KbChunk, KbDocument
from ..providers import embeddings

_ROOT = Path(os.getenv("ASSISTANT_INDEX_ROOT", str(Path(__file__).resolve().parents[4])))

# extension → KB source_type
_EXT_TYPE = {".md": "doc", ".py": "code", ".tsx": "code", ".ts": "code", ".html": "guide"}
_EXCLUDE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "coverage", "htmlcov", "logs",
}
# Secret-bearing or noisy files are never indexed (ticket §10).
_EXCLUDE_NAME_RE = re.compile(
    r"(^\.env)|(\.env$)|(seed.*\.py$)|(seed_mock)|(package-lock\.json$)|(\.lock$)|(\.min\.(js|css)$)",
    re.IGNORECASE,
)
_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|passwd|token|private[_-]?key|BEGIN [A-Z ]*PRIVATE KEY|"
    r"AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,})\s*[:=]\s*['\"][^'\"]{6,}",
)
_MAX_FILE_BYTES = 200_000
_CHUNK = 1200
_OVERLAP = 150


@dataclass
class IndexStats:
    version: int
    doc_count: int
    chunk_count: int
    skipped_secret: int
    degraded: bool


def _iter_files() -> list[Path]:
    out: list[Path] = []
    roots = [
        _ROOT / "docs", _ROOT / "backend" / "app", _ROOT / "web" / "src" / "content",
    ]
    singles = [
        _ROOT / "README.md", _ROOT / "DESIGN.md", _ROOT / "whitemoon-user-guide.html",
    ]
    for base in roots:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_dir():
                continue
            if any(part in _EXCLUDE_DIRS for part in p.parts):
                continue
            if p.suffix.lower() not in _EXT_TYPE:
                continue
            if _EXCLUDE_NAME_RE.search(p.name):
                continue
            out.append(p)
    out.extend(s for s in singles if s.exists())
    return out


def _gitleaks_clean(path: Path) -> bool:
    """True if the file passes gitleaks; falls back to the regex guard when the
    gitleaks binary isn't installed."""
    exe = shutil.which("gitleaks")
    if exe:  # pragma: no cover - requires the binary
        try:
            r = subprocess.run(
                [exe, "detect", "--no-git", "--redact", "-s", str(path)],
                capture_output=True, timeout=30,
            )
            return r.returncode == 0
        except Exception:
            pass
    try:
        return _SECRET_RE.search(path.read_text("utf-8", errors="ignore")) is None
    except Exception:
        return True


def _chunks(text: str) -> list[str]:
    text = text.strip()
    if len(text) <= _CHUNK:
        return [text] if text else []
    out: list[str] = []
    i = 0
    while i < len(text):
        out.append(text[i : i + _CHUNK])
        i += _CHUNK - _OVERLAP
    return out


def reindex(*, git_sha: str | None = None) -> IndexStats:
    version = (db.session.execute(select(IndexVersion.version).order_by(IndexVersion.version.desc()).limit(1)).scalar_one_or_none() or 0) + 1
    iv = IndexVersion(version=version, status="running", git_sha=git_sha, started_at=datetime.now(UTC))
    db.session.add(iv)
    db.session.commit()

    doc_count = chunk_count = skipped = 0
    try:
        for path in _iter_files():
            try:
                if path.stat().st_size > _MAX_FILE_BYTES:
                    continue
                if not _gitleaks_clean(path):
                    skipped += 1
                    continue
                raw = path.read_text("utf-8", errors="ignore")
            except Exception:
                continue
            chunks = _chunks(raw)
            if not chunks:
                continue
            rel = str(path.relative_to(_ROOT)).replace("\\", "/")
            stype = _EXT_TYPE.get(path.suffix.lower(), "doc")
            if rel == "README.md":
                stype = "readme"
            doc = KbDocument(
                source_path=rel, source_type=stype, title=path.name,
                content_hash=hashlib.sha256(raw.encode("utf-8")).hexdigest(), index_version=version,
            )
            db.session.add(doc)
            db.session.flush()
            vecs = embeddings.embed_texts(chunks)
            for ordinal, (ctext, vec) in enumerate(zip(chunks, vecs, strict=True)):
                db.session.add(
                    KbChunk(
                        document_id=doc.id, index_version=version, ordinal=ordinal,
                        source_path=rel, source_type=stype, title=path.name,
                        text=ctext, token_count=len(ctext) // 4, embedding=vec,
                    )
                )
                chunk_count += 1
            doc_count += 1
            db.session.commit()

        iv.status = "ready"
        iv.doc_count = doc_count
        iv.chunk_count = chunk_count
        iv.degraded = embeddings.is_degraded()
        iv.finished_at = datetime.now(UTC)
        db.session.commit()

        # Prune older versions now that the new one is ready.
        old = [v for (v,) in db.session.execute(select(IndexVersion.version).where(IndexVersion.version < version)).all()]
        if old:
            db.session.execute(delete(KbChunk).where(KbChunk.index_version.in_(old)))
            db.session.execute(delete(KbDocument).where(KbDocument.index_version.in_(old)))
            db.session.execute(delete(IndexVersion).where(IndexVersion.version.in_(old)))
            db.session.commit()
    except Exception:
        iv.status = "failed"
        iv.finished_at = datetime.now(UTC)
        db.session.commit()
        raise

    return IndexStats(
        version=version, doc_count=doc_count, chunk_count=chunk_count,
        skipped_secret=skipped, degraded=iv.degraded,
    )

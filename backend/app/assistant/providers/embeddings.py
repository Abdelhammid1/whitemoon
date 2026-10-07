"""Local embeddings for RAG (ticket §20 — embeddings must be local/open).

Primary: a local Sentence-Transformers model (default `BAAI/bge-m3`, strong on
Arabic) loaded once per process. It never calls out to any API.

Fallback: when the model (or torch) is not installed, a deterministic
hashing-based embedding so the whole pipeline still runs in dev/CI. It carries
real lexical signal (good enough for tests) and is flagged as *degraded* so the
admin sees that retrieval quality is reduced until the real model is installed.

Answer generation is never done here — only DeepSeek generates answers.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import threading

from ..models import EMBED_DIM

_MODEL_NAME = os.getenv("ASSISTANT_EMBED_MODEL", "BAAI/bge-m3")
_lock = threading.Lock()
_model: object | None = None
_tried = False


def _load_model() -> object | None:
    global _model, _tried
    if _tried:
        return _model
    with _lock:
        if _tried:
            return _model
        _tried = True
        try:  # pragma: no cover - heavy optional dependency
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(_MODEL_NAME)
        except Exception:
            _model = None
        return _model


def is_degraded() -> bool:
    """True when the real embedding model is unavailable (fallback in use)."""
    return _load_model() is None


_token_re = re.compile(r"[\w؀-ۿ]+", re.UNICODE)


def _hash_embed(text: str) -> list[float]:
    """Deterministic signed hashing-trick embedding, L2-normalised."""
    vec = [0.0] * EMBED_DIM
    toks = _token_re.findall(text.lower())
    for tok in toks:
        h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(h[:4], "little") % EMBED_DIM
        sign = 1.0 if h[4] & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _load_model()
    if model is not None:  # pragma: no cover - requires the model
        vecs = model.encode(texts, normalize_embeddings=True)  # type: ignore[attr-defined]
        return [list(map(float, v)) for v in vecs]
    return [_hash_embed(t) for t in texts]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]

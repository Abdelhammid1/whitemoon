"""Object storage for uploaded files (receipt images, …).

Writes to S3/MinIO when `S3_BUCKET` is configured (prod), otherwise to a local
directory (dev). Callers get back an opaque storage *key*; the bytes are never
kept in the database. Keys are server-generated (UUID) so a client filename can
never cause path traversal or collisions.
"""

from __future__ import annotations

import os
import pathlib
import uuid

# Keep uploads modest — receipts are photos/scans, not archives.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


def _local_root() -> pathlib.Path:
    root = pathlib.Path(os.getenv("UPLOAD_DIR", "var/uploads"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _s3_client():  # pragma: no cover - exercised only when S3 is configured
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT") or None,
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
        region_name=os.getenv("S3_REGION", "us-east-1"),
    )


def safe_extension(filename: str | None) -> str:
    """Return a lowercase allowed extension, or raise ValueError."""
    ext = pathlib.Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"unsupported file type: {ext or 'unknown'}")
    return ext


def store(data: bytes, *, prefix: str, ext: str) -> str:
    """Persist bytes and return a storage key. `ext` includes the dot."""
    key = f"{prefix}/{uuid.uuid4().hex}{ext}"
    bucket = os.getenv("S3_BUCKET")
    if bucket:  # pragma: no cover - needs a live bucket
        _s3_client().put_object(Bucket=bucket, Key=key, Body=data)
        return key
    path = _local_root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key


def load(key: str) -> bytes | None:
    bucket = os.getenv("S3_BUCKET")
    if bucket:  # pragma: no cover - needs a live bucket
        try:
            return _s3_client().get_object(Bucket=bucket, Key=key)["Body"].read()
        except Exception:
            return None
    path = _local_root() / key
    # Guard against traversal: the resolved path must stay under the root.
    try:
        path.resolve().relative_to(_local_root().resolve())
    except ValueError:
        return None
    return path.read_bytes() if path.exists() else None

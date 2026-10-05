"""Object storage for uploaded files (receipt images, …).

Writes to S3/MinIO when a bucket is configured for the concern (prod/staging),
otherwise to a local directory (dev). Callers get back an opaque storage *key*
of the form ``<concern>/<uuid><ext>``; the bytes are never kept in the database.
Keys are server-generated (UUID) so a client filename can never cause path
traversal or collisions.

Bucket names are per-concern and resolved from the environment to match
`.env.example`: ``S3_BUCKET_RECEIPTS`` / ``S3_BUCKET_CHAT`` / ``S3_BUCKET_KYC``
/ ``S3_BUCKET_INVOICES`` (a generic ``S3_BUCKET`` is used as a fallback). The
endpoint comes from ``S3_ENDPOINT_URL`` (legacy ``S3_ENDPOINT`` still honored).
With no matching bucket set, storage falls back to the local filesystem.
"""

from __future__ import annotations

import os
import pathlib
import uuid

# Keep uploads modest — receipts are photos/scans, not archives.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}

# concern (key prefix) -> the env var holding its bucket name.
_BUCKET_ENV = {
    "receipts": "S3_BUCKET_RECEIPTS",
    "chat": "S3_BUCKET_CHAT",
    "kyc": "S3_BUCKET_KYC",
    "invoices": "S3_BUCKET_INVOICES",
}


def _local_root() -> pathlib.Path:
    root = pathlib.Path(os.getenv("UPLOAD_DIR", "var/uploads"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _bucket_for(concern: str) -> str | None:
    """The configured bucket for a concern, or the generic fallback, or None."""
    env = _BUCKET_ENV.get(concern)
    return (os.getenv(env) if env else None) or os.getenv("S3_BUCKET")


def _s3_client():  # pragma: no cover - exercised only when S3 is configured
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL") or os.getenv("S3_ENDPOINT") or None,
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
    """Persist bytes and return a storage key. `ext` includes the dot.
    `prefix` is the concern (e.g. "receipts") and selects the bucket."""
    key = f"{prefix}/{uuid.uuid4().hex}{ext}"
    bucket = _bucket_for(prefix)
    if bucket:  # pragma: no cover - needs a live bucket
        _s3_client().put_object(Bucket=bucket, Key=key, Body=data)
        return key
    path = _local_root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key


def load(key: str) -> bytes | None:
    # The concern is the first path segment of the key.
    concern = key.split("/", 1)[0]
    bucket = _bucket_for(concern)
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

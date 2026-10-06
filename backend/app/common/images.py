"""Shared raster-image validation for user uploads.

Uploads are validated by *signature*, not by the client-supplied extension or
MIME type, so an SVG, HTML page or script renamed to `.png` is rejected before
it is ever stored — the defence against stored-XSS behind image endpoints.
"""

from __future__ import annotations

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def is_raster_image(data: bytes) -> bool:
    """Signature sniff — rejects SVG/HTML/scripts regardless of extension."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:3] == b"\xff\xd8\xff":  # JPEG
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False


def mime_for_key(key: str) -> str:
    """Server-decided content type for a stored key (never trust the client)."""
    ext = "." + key.rsplit(".", 1)[-1].lower() if "." in key else ""
    return IMAGE_MIME.get(ext, "application/octet-stream")

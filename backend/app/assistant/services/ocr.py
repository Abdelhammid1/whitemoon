"""Local text extraction for uploads (ticket §13).

Images → Tesseract OCR (Arabic+English). PDFs → embedded text via pypdf when
available. Everything runs locally; the original file is held only in memory and
NEVER sent anywhere. The extracted text is redaction-cleaned by the caller
before it can reach DeepSeek.
"""

from __future__ import annotations

import io

from ...common.images import is_raster_image

MAX_OCR_CHARS = 8000


class OcrUnavailable(RuntimeError):
    pass


def extract_text(data: bytes, *, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf") or data[:5] == b"%PDF-":
        return _pdf_text(data)[:MAX_OCR_CHARS]
    if not is_raster_image(data):
        raise OcrUnavailable("نوع الملف غير مدعوم — ارفع صورة (PNG/JPG) أو PDF.")
    return _image_text(data)[:MAX_OCR_CHARS]


def _image_text(data: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
    except Exception as e:  # pragma: no cover
        raise OcrUnavailable("القراءة الضوئية غير متاحة على الخادم.") from e
    try:
        img = Image.open(io.BytesIO(data))
        # Arabic+English; falls back to default if the language packs are absent.
        try:
            return pytesseract.image_to_string(img, lang="ara+eng")
        except Exception:
            return pytesseract.image_to_string(img)
    except Exception as e:
        raise OcrUnavailable("تعذّر قراءة الصورة.") from e


def _pdf_text(data: bytes) -> str:
    try:  # pragma: no cover - optional dependency
        from pypdf import PdfReader
    except Exception as e:
        raise OcrUnavailable("استخراج نص PDF غير متاح على الخادم.") from e
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages[:20])
    except Exception as e:
        raise OcrUnavailable("تعذّر قراءة ملف PDF.") from e

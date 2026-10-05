"""Pluggable receipt-OCR provider.

v1 ships a `stub` provider for dev and tests — the caller feeds the
desired fields in via a side-channel (e.g. request body) and the stub
echoes them back. Real engines (Tesseract via pytesseract, hosted
Document AI, Textract-compatible) plug in behind the same protocol.
"""

from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

# Map Arabic-Indic and Persian digits to ASCII so parsing is uniform.
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

# Receipts are ordinary phone photos; cap decoded pixels to bound OCR cost.
_MAX_IMAGE_PIXELS = 25_000_000  # ~25 MP


def parse_amount(text: str) -> Decimal | None:
    """Best-effort transfer amount from OCR text. Prefers money-formatted
    numbers (decimals / thousands grouping) so a long reference id is not
    mistaken for the amount; falls back to short integers."""
    t = text.translate(_AR_DIGITS)
    money = re.findall(r"\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+\.\d{1,2}", t)
    vals: list[Decimal] = []
    for c in money:
        try:
            v = Decimal(c.replace(",", ""))
        except InvalidOperation:
            continue
        if v > 0:
            vals.append(v)
    if vals:
        return max(vals)
    ints = [Decimal(c) for c in re.findall(r"\b\d{1,6}\b", t)]
    ints = [v for v in ints if v > 0]
    return max(ints) if ints else None


def parse_reference(text: str) -> str | None:
    """Transaction/reference number: the longest digit run of ≥6 digits."""
    refs = re.findall(r"\d{6,}", text.translate(_AR_DIGITS))
    return max(refs, key=len) if refs else None


def _ocr_text(image_bytes: bytes) -> str:
    import pytesseract
    from PIL import Image

    cmd = os.getenv("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    img = Image.open(io.BytesIO(image_bytes))
    # Guard against decompression bombs: a small upload can decode to a huge
    # pixel grid and exhaust memory/CPU in OCR. Receipts are ordinary photos,
    # so cap the pixel count (raises → caught by extract → manual review).
    w, h = img.size
    if w * h > _MAX_IMAGE_PIXELS:
        raise ValueError("image too large for OCR")
    return pytesseract.image_to_string(img, lang=os.getenv("OCR_LANG", "ara+eng"))


@dataclass(frozen=True)
class OcrResult:
    amount: Decimal | None
    reference: str | None
    raw: dict[str, Any]


class OcrProvider(Protocol):
    def extract(self, image_bytes: bytes) -> OcrResult: ...


class StubProvider:
    """Dev/test — returns whatever `prime()` was last given."""

    def __init__(self) -> None:
        self._primed: OcrResult = OcrResult(amount=None, reference=None, raw={})

    def prime(self, *, amount: Decimal | None, reference: str | None) -> None:
        self._primed = OcrResult(
            amount=amount, reference=reference, raw={"stub": True}
        )

    def extract(self, image_bytes: bytes) -> OcrResult:  # noqa: ARG002
        return self._primed


class TesseractProvider:
    """Real OCR via pytesseract (same engine as chat image scanning). Extracts
    the transfer amount + reference. If OCR can't run (missing binary/bad
    image), it returns an empty result so the caller routes the receipt to
    manual review rather than failing the upload (US-3.3)."""

    def extract(self, image_bytes: bytes) -> OcrResult:
        try:
            text = _ocr_text(image_bytes)
        except Exception as e:
            return OcrResult(
                amount=None, reference=None,
                raw={"engine": "tesseract", "error": type(e).__name__},
            )
        return OcrResult(
            amount=parse_amount(text),
            reference=parse_reference(text),
            raw={"engine": "tesseract", "text_len": len(text)},
        )


_singleton_stub = StubProvider()


def get_provider(name: str) -> OcrProvider:
    if name == "stub":
        return _singleton_stub
    if name == "tesseract":
        return TesseractProvider()
    raise ValueError(f"Unknown OCR provider: {name}")


def get_stub() -> StubProvider:
    """Expose the singleton stub so tests can `prime()` it."""
    return _singleton_stub

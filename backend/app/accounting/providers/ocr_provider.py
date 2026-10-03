"""Pluggable receipt-OCR provider.

v1 ships a `stub` provider for dev and tests — the caller feeds the
desired fields in via a side-channel (e.g. request body) and the stub
echoes them back. Real engines (Tesseract via pytesseract, hosted
Document AI, Textract-compatible) plug in behind the same protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol


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
    """Phase 2 ops task — real pytesseract wiring lands here."""

    def extract(self, image_bytes: bytes) -> OcrResult:  # pragma: no cover
        _ = image_bytes
        raise NotImplementedError("TesseractProvider is a Phase 2 ops task")


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

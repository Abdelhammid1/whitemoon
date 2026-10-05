"""Receipt OCR parsing (US-3.3). Parsing is pure; the extract() error path
needs neither the Tesseract binary nor a real image."""

from __future__ import annotations

from decimal import Decimal

from app.accounting.providers import ocr_provider as ocr


def test_parse_amount_prefers_money_format(client) -> None:
    txt = "رقم العملية 123456789\nالمبلغ 1,500.00 ج.م"
    assert ocr.parse_amount(txt) == Decimal("1500.00")
    assert ocr.parse_reference(txt) == "123456789"


def test_parse_handles_arabic_digits(client) -> None:
    txt = "المبلغ ٢٥٠٠.٠٠ مرجع ٩٨٧٦٥٤٣٢"
    assert ocr.parse_amount(txt) == Decimal("2500.00")
    assert ocr.parse_reference(txt) == "98765432"


def test_amount_not_confused_by_long_reference(client) -> None:
    # The 12-digit reference is numerically larger but must not be the amount.
    txt = "trx 998877665544 total 250.75 EGP"
    assert ocr.parse_amount(txt) == Decimal("250.75")
    assert ocr.parse_reference(txt) == "998877665544"


def test_tesseract_extract_graceful_on_bad_image(client) -> None:
    # No binary/invalid image → empty result so the receipt goes to manual
    # review instead of failing the upload.
    r = ocr.get_provider("tesseract").extract(b"not-an-image")
    assert r.amount is None and r.reference is None
    assert r.raw.get("engine") == "tesseract"

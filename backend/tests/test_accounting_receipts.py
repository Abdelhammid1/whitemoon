"""Bank-receipt OCR match flow (US-3.3) via the stub provider."""

from __future__ import annotations

from decimal import Decimal

from app.accounting.providers.ocr_provider import get_stub
from app.accounting.services import receipts as receipts_svc
from app.extensions import db


def test_matching_values_mark_receipt_matched(client) -> None:
    get_stub().prime(amount=Decimal("500"), reference="REF-1")
    result = receipts_svc.upload_and_match(
        uploaded_by=1,
        image_s3_key="dev/receipt-1.jpg",
        image_bytes=b"",
        expected_amount=Decimal("500"),
        expected_reference="REF-1",
    )
    db.session.commit()
    assert result.status == "matched"


def test_mismatched_amount_routes_to_manual_review(client) -> None:
    get_stub().prime(amount=Decimal("499"), reference="REF-2")
    result = receipts_svc.upload_and_match(
        uploaded_by=1,
        image_s3_key="dev/receipt-2.jpg",
        image_bytes=b"",
        expected_amount=Decimal("500"),
        expected_reference="REF-2",
    )
    db.session.commit()
    assert result.status == "manual_review"


def test_no_expectation_routes_to_manual_review(client) -> None:
    get_stub().prime(amount=Decimal("500"), reference="REF-3")
    result = receipts_svc.upload_and_match(
        uploaded_by=1,
        image_s3_key="dev/receipt-3.jpg",
        image_bytes=b"",
    )
    db.session.commit()
    assert result.status == "manual_review"

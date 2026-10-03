"""Bank-receipt upload + OCR match (US-3.3)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal

from ...common.errors import NotFound
from ...common.money import to_money
from ...extensions import db
from ..models import BankReceipt
from ..providers.ocr_provider import get_provider


@dataclass(frozen=True)
class ReceiptUploadResult:
    receipt_id: int
    status: str
    ocr_amount: Decimal | None
    ocr_reference: str | None


def upload_and_match(
    *,
    uploaded_by: int,
    image_s3_key: str,
    image_bytes: bytes,
    expected_amount: Decimal | None = None,
    expected_reference: str | None = None,
) -> ReceiptUploadResult:
    """Store the receipt, run OCR, auto-match if possible, else route to
    manual review.

    v1 "match" means: OCR amount == expected amount AND OCR reference ==
    expected reference. Mismatch → `manual_review` with a reason.
    """
    provider_name = os.getenv("OCR_PROVIDER", "stub")
    provider = get_provider(provider_name)
    ocr = provider.extract(image_bytes)
    amount = to_money(ocr.amount) if ocr.amount is not None else None

    receipt = BankReceipt(
        uploaded_by=uploaded_by,
        image_s3_key=image_s3_key,
        ocr_amount=amount,
        ocr_reference=ocr.reference,
        ocr_raw_json=ocr.raw,
        status="pending",
    )
    db.session.add(receipt)
    db.session.flush()

    if expected_amount is not None and expected_reference is not None:
        if amount == to_money(expected_amount) and ocr.reference == expected_reference:
            receipt.status = "matched"
        else:
            receipt.status = "manual_review"
            diffs: list[str] = []
            if amount != to_money(expected_amount):
                diffs.append(f"amount expected={expected_amount} ocr={amount}")
            if ocr.reference != expected_reference:
                diffs.append(
                    f"reference expected={expected_reference} ocr={ocr.reference}"
                )
            receipt.manual_review_reason = "; ".join(diffs)
    else:
        receipt.status = "manual_review"
        receipt.manual_review_reason = "no expected values supplied"

    db.session.flush()
    return ReceiptUploadResult(
        receipt_id=receipt.id,
        status=receipt.status,
        ocr_amount=amount,
        ocr_reference=ocr.reference,
    )


def resolve_manual_review(
    *,
    receipt_id: int,
    status: str,
    resolved_by: int,  # noqa: ARG001 — captured in audit at the route layer
) -> BankReceipt:
    receipt = db.session.get(BankReceipt, receipt_id)
    if receipt is None:
        raise NotFound("Receipt not found", code="receipt_not_found")
    if status not in ("matched", "rejected"):
        raise ValueError("status must be matched or rejected")
    receipt.status = status
    db.session.flush()
    return receipt

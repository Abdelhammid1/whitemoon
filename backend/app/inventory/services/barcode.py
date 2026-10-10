"""Barcode identity for products (T-31).

- Global barcodes (EAN-13 / UPC-A) are validated by their check digit and are
  the product's identity; no internal code is generated for them.
- A local product with no barcode gets an auto internal code `WM-000001` (6
  digits), printable as a scannable label.
"""

from __future__ import annotations

import re

from sqlalchemy import func, select

from ...common.errors import BadRequest
from ...extensions import db
from ..models import Product

_INTERNAL_RE = re.compile(r"^WM-(\d{6})$")


def _check_digit_ean13(payload12: str) -> int:
    # positions 1..12 left→right: odd×1, even×3; check makes total ≡ 0 (mod 10).
    s = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(payload12))
    return (10 - (s % 10)) % 10


def _check_digit_upca(payload11: str) -> int:
    # positions 1..11 left→right: odd×3, even×1.
    s = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(payload11))
    return (10 - (s % 10)) % 10


def is_valid_barcode(code: str) -> bool:
    code = (code or "").strip()
    if not code.isdigit():
        return False
    if len(code) == 13:
        return _check_digit_ean13(code[:12]) == int(code[12])
    if len(code) == 12:
        return _check_digit_upca(code[:11]) == int(code[11])
    return False


def validate_barcode(code: str) -> str:
    """Return the normalised barcode, or raise with an Arabic message (T-31)."""
    code = (code or "").strip()
    if not is_valid_barcode(code):
        raise BadRequest(
            "باركود غير صالح — يجب أن يكون EAN-13 أو UPC-A برقم مراجعة صحيح",
            code="barcode_invalid",
        )
    return code


def next_internal_code() -> str:
    """The next `WM-NNNNNN` internal code for a local (barcode-less) product.
    Derived from the highest existing WM sku; a race is caught by the sku unique
    constraint (admin-paced creation), so the caller simply retries."""
    rows = db.session.execute(
        select(Product.sku).where(Product.sku.like("WM-%"))
    ).scalars().all()
    highest = 0
    for sku in rows:
        m = _INTERNAL_RE.match(sku)
        if m:
            highest = max(highest, int(m.group(1)))
    return f"WM-{highest + 1:06d}"


def barcode_in_use(code: str, *, exclude_product_id: int | None = None) -> bool:
    """True if another product already carries this barcode (uniqueness, T-31)."""
    stmt = select(func.count()).select_from(Product).where(Product.barcode == code)
    if exclude_product_id is not None:
        stmt = stmt.where(Product.id != exclude_product_id)
    return int(db.session.execute(stmt).scalar_one()) > 0

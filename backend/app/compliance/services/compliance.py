"""ETA readiness + EGP-only guard — EPIC 11.

US-11.1: mark products with an ETA item code and a readiness flag, and report
readiness — no live tax-authority API call in this version.
US-11.2: the EGP-only rule is enforced structurally by a `currency = 'EGP'`
CHECK on every monetary table; `assert_egp` is the matching runtime guard for
any code path that takes a currency.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ...common.errors import BadRequest, NotFound
from ...common.money import CURRENCY
from ...extensions import db
from ...identity.services.audit import emit as audit_emit
from ...inventory.models import Product


def assert_egp(currency: str) -> None:
    """Reject any non-EGP currency between parties inside Egypt (US-11.2)."""
    if currency != CURRENCY:
        raise BadRequest(
            "العملة يجب أن تكون الجنيه المصري فقط", code="currency_must_be_egp"
        )


def set_eta(
    *, product_id: int, eta_code: str | None, eta_ready: bool, actor_user_id: int
) -> Product:
    product = db.session.get(Product, product_id)
    if product is None:
        raise NotFound("المنتج غير موجود", code="product_not_found")
    # Can't be ETA-ready without an item code to report.
    if eta_ready and not (eta_code or product.eta_code):
        raise BadRequest("كود الصنف (ETA) مطلوب للجاهزية", code="eta_code_required")
    if eta_code is not None:
        product.eta_code = eta_code.strip() or None
    product.eta_ready = eta_ready
    audit_emit("compliance.eta.set", actor_user_id=actor_user_id, target_type="product", target_id=product.id)
    db.session.commit()
    return product


def readiness_report() -> dict[str, Any]:
    products = list(db.session.execute(select(Product)).scalars())
    total = len(products)
    ready = sum(1 for p in products if p.eta_ready)
    missing_code = [p.id for p in products if not p.eta_code]
    return {
        "total_products": total,
        "eta_ready": ready,
        "not_ready": total - ready,
        "missing_eta_code": missing_code,
        "currency": CURRENCY,
    }


def serialize_product_eta(p: Product) -> dict[str, Any]:
    return {
        "product_id": p.id,
        "sku": p.sku,
        "eta_code": p.eta_code,
        "eta_ready": p.eta_ready,
    }

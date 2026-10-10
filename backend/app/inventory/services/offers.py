"""Supplier offers + server-side best-price (US-1.1, US-4.1).

Supplier-isolation rules:
- A supplier manages only their own offers (ownership checked at the route).
- `best_offer` returns the lowest active price WITHOUT the supplier id, so
  no customer-facing path can learn who the supplier is.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from ...common.errors import BadRequest, NotFound
from ...common.money import to_money
from ...extensions import db
from ..models import Product, SupplierOffer

# The exact rejection message (T-30): it leaks NO price and NO supplier name.
REJECT_DISCOUNT_MSG = "لا يمكن قبول هذا الخصم لأنه لا يحقق أفضل سعر على المنصة. اختر سعرًا أقل."
DISCOUNT_KINDS = ("none", "percent", "price")


def _discount_active(offer: SupplierOffer, on: date) -> bool:
    if offer.discount_kind == "none" or offer.discount_value is None:
        return False
    if offer.discount_start is not None and on < offer.discount_start:
        return False
    if offer.discount_end is not None and on > offer.discount_end:
        return False
    return True


def effective_price(offer: SupplierOffer, on: date | None = None) -> Decimal:
    """The price a customer would pay today: the unit price, or the discounted
    price when a discount is active."""
    on = on or date.today()
    if _discount_active(offer, on):
        if offer.discount_kind == "percent" and offer.discount_value is not None:
            return to_money(offer.unit_price * (Decimal("1") - to_money(offer.discount_value) / Decimal("100")))
        if offer.discount_kind == "price" and offer.discount_value is not None:
            return to_money(offer.discount_value)
    return to_money(offer.unit_price)


def discounted_price_for(*, unit_price: Decimal, discount_kind: str, discount_value: Decimal | None) -> Decimal:
    """The price a given discount shape would produce off `unit_price`."""
    up = to_money(unit_price)
    if discount_kind == "percent" and discount_value is not None:
        return to_money(up * (Decimal("1") - to_money(discount_value) / Decimal("100")))
    if discount_kind == "price" and discount_value is not None:
        return to_money(discount_value)
    return up


def _lowest_other_effective(*, product_id: int, supplier_id: int, on: date | None = None) -> Decimal | None:
    """Lowest active effective price among OTHER suppliers for a product."""
    on = on or date.today()
    others = db.session.execute(
        select(SupplierOffer).where(
            SupplierOffer.product_id == product_id,
            SupplierOffer.is_active.is_(True),
            SupplierOffer.supplier_id != supplier_id,
        )
    ).scalars().all()
    best: Decimal | None = None
    for o in others:
        ep = effective_price(o, on)
        if best is None or ep < best:
            best = ep
    return best


def validate_discount(*, product_id: int, supplier_id: int, discounted_price: Decimal) -> None:
    """A discount is only accepted when it achieves the platform-best price:
    strictly below every other supplier's active effective price. Raises the
    exact, leak-free message otherwise (T-30)."""
    best_other = _lowest_other_effective(product_id=product_id, supplier_id=supplier_id)
    if best_other is not None and to_money(discounted_price) >= best_other:
        raise BadRequest(REJECT_DISCOUNT_MSG, code="discount_not_best")


def _notify_undercut(*, product_id: int, new_effective: Decimal, except_supplier_id: int) -> None:
    """When a supplier's new price undercuts another supplier's ACTIVE discount
    (so that discount no longer achieves best price), notify that supplier — we
    never auto-cancel their discount (T-30). Never raises."""
    try:
        from ...notifications.services import notify as notify_svc

        today = date.today()
        affected = db.session.execute(
            select(SupplierOffer).where(
                SupplierOffer.product_id == product_id,
                SupplierOffer.is_active.is_(True),
                SupplierOffer.supplier_id != except_supplier_id,
            )
        ).scalars().all()
        for o in affected:
            if _discount_active(o, today) and effective_price(o, today) > to_money(new_effective):
                notify_svc.notify(
                    user_id=o.supplier_id,
                    title="خصمك لم يعد أفضل سعر",
                    body="نزل سعر منافس على أحد أصنافك تحت سعر خصمك. راجع سعرك أو خصمك للحفاظ على أفضل سعر.",
                    type_="discount_outbid",
                    channel="in_app",
                )
    except Exception:  # pragma: no cover - notifications must never block a price change
        pass


def upsert_offer(
    *,
    supplier_id: int,
    product_id: int,
    unit_price: Decimal,
    moq: Decimal = Decimal("0"),
    is_active: bool = True,
    discount_kind: str = "none",
    discount_value: Decimal | None = None,
    discount_start: date | None = None,
    discount_end: date | None = None,
) -> SupplierOffer:
    product = db.session.get(Product, product_id)
    if product is None:
        raise NotFound("Product not found", code="product_not_found")

    if discount_kind not in DISCOUNT_KINDS:
        raise BadRequest("نوع خصم غير صالح", code="bad_discount_kind")
    if discount_kind != "none":
        if discount_value is None or to_money(discount_value) <= 0:
            raise BadRequest("قيمة الخصم مطلوبة وموجبة", code="discount_value_required")
        disc_price = discounted_price_for(
            unit_price=unit_price, discount_kind=discount_kind, discount_value=discount_value
        )
        if disc_price <= 0:
            raise BadRequest("السعر بعد الخصم يجب أن يكون موجبًا", code="discount_price_nonpositive")
        validate_discount(product_id=product_id, supplier_id=supplier_id, discounted_price=disc_price)

    offer = db.session.execute(
        select(SupplierOffer).where(
            SupplierOffer.supplier_id == supplier_id,
            SupplierOffer.product_id == product_id,
        )
    ).scalar_one_or_none()
    if offer is None:
        offer = SupplierOffer(
            supplier_id=supplier_id,
            product_id=product_id,
            unit_price=to_money(unit_price),
            moq=to_money(moq),
            is_active=is_active,
        )
        db.session.add(offer)
    else:
        # Price-lock guard (US-1.6): a raise is rejected while any lock on
        # this offer is live; a cut is allowed and lowers the live locks.
        from ...commerce.services import pricelock

        pricelock.enforce_price_change(
            offer_id=offer.id, current_price=offer.unit_price, new_price=to_money(unit_price)
        )
        offer.unit_price = to_money(unit_price)
        offer.moq = to_money(moq)
        offer.is_active = is_active
    offer.discount_kind = discount_kind
    offer.discount_value = to_money(discount_value) if discount_value is not None and discount_kind != "none" else None
    offer.discount_start = discount_start if discount_kind != "none" else None
    offer.discount_end = discount_end if discount_kind != "none" else None
    db.session.commit()
    _notify_undercut(
        product_id=product_id, new_effective=effective_price(offer), except_supplier_id=supplier_id
    )
    return offer


def lower_price_exists(*, product_id: int, my_price: Decimal) -> bool:
    """True if any active offer on this product is cheaper than `my_price` —
    without revealing the competitor's identity or exact price (US-1.5)."""
    cheaper = db.session.execute(
        select(SupplierOffer.id)
        .where(
            SupplierOffer.product_id == product_id,
            SupplierOffer.is_active.is_(True),
            SupplierOffer.unit_price < to_money(my_price),
        )
        .limit(1)
    ).first()
    return cheaper is not None


def list_offers_for_supplier(supplier_id: int) -> list[SupplierOffer]:
    stmt = (
        select(SupplierOffer)
        .where(SupplierOffer.supplier_id == supplier_id)
        .order_by(SupplierOffer.id.desc())
    )
    return list(db.session.execute(stmt).scalars().all())


def best_offer(product_id: int) -> dict[str, Any] | None:
    """Lowest active offer for a product. NEVER returns supplier identity."""
    stmt = (
        select(SupplierOffer.unit_price, SupplierOffer.moq)
        .where(
            SupplierOffer.product_id == product_id,
            SupplierOffer.is_active.is_(True),
        )
        .order_by(SupplierOffer.unit_price.asc())
        .limit(1)
    )
    row = db.session.execute(stmt).one_or_none()
    if row is None:
        return None
    return {"best_price": str(to_money(row.unit_price)), "moq": str(to_money(row.moq))}


def serialize_own(offer: SupplierOffer) -> dict[str, Any]:
    """Full detail — only ever returned to the owning supplier or an admin.

    Includes the `lower_price_exists` hint (US-1.5): a bare signal that a
    cheaper competing offer exists, with no competitor identity or price.
    """
    return {
        "id": offer.id,
        "product_id": offer.product_id,
        "unit_price": str(offer.unit_price),
        "moq": str(offer.moq),
        "is_active": offer.is_active,
        "currency": offer.currency,
        "discount_kind": offer.discount_kind,
        "discount_value": str(offer.discount_value) if offer.discount_value is not None else None,
        "discount_start": offer.discount_start.isoformat() if offer.discount_start else None,
        "discount_end": offer.discount_end.isoformat() if offer.discount_end else None,
        "effective_price": str(effective_price(offer)),
        "lower_price_exists": lower_price_exists(
            product_id=offer.product_id, my_price=offer.unit_price
        ),
    }


def supplier_products(supplier_id: int) -> list[dict[str, Any]]:
    """The unified «منتجاتي» view (T-30): every product this supplier offers or
    stocks, with catalog metadata (name/barcode/image — allowed), the supplier's
    price + discount + moq + active, and their on-hand/available at their own
    warehouse. Supplier identity of OTHER suppliers is never exposed."""
    from ..models import StockBalance

    offers = {
        o.product_id: o
        for o in db.session.execute(
            select(SupplierOffer).where(SupplierOffer.supplier_id == supplier_id)
        ).scalars()
    }
    balances = {
        b.product_id: b
        for b in db.session.execute(
            select(StockBalance).where(
                StockBalance.supplier_id == supplier_id,
                StockBalance.location_type == "supplier",
                StockBalance.location_id.is_(None),
            )
        ).scalars()
    }
    product_ids = set(offers) | set(balances)
    if not product_ids:
        return []
    products = {
        p.id: p
        for p in db.session.execute(
            select(Product).where(Product.id.in_(product_ids))
        ).scalars()
    }
    out: list[dict[str, Any]] = []
    for pid in product_ids:
        p = products.get(pid)
        if p is None:
            continue
        o = offers.get(pid)
        b = balances.get(pid)
        on_hand = to_money(b.on_hand) if b is not None else Decimal("0")
        reserved = to_money(b.reserved) if b is not None else Decimal("0")
        row: dict[str, Any] = {
            "product_id": pid,
            "name": p.name_ar,
            "barcode": p.barcode,
            "image_url": p.image_url,
            "category": p.category,
            "on_hand": str(on_hand),
            "available": str(on_hand - reserved),
            "reorder_point": str(b.reorder_point) if b is not None and b.reorder_point is not None else None,
            "offer": serialize_own(o) if o is not None else None,
        }
        out.append(row)
    out.sort(key=lambda r: r["name"] or "")
    return out


def set_supplier_product(
    *,
    supplier_id: int,
    product_id: int,
    unit_price: Decimal,
    on_hand: Decimal | None = None,
    moq: Decimal = Decimal("0"),
    is_active: bool = True,
    discount_kind: str = "none",
    discount_value: Decimal | None = None,
    discount_start: date | None = None,
    discount_end: date | None = None,
    reorder_point: Decimal | None = None,
) -> dict[str, Any]:
    """One-call update of a supplier's product (T-30): price + discount + moq +
    active (the offer) and the on-hand quantity (their own warehouse). The
    discount is validated for best-price before anything is written."""
    from . import stock as stock_svc

    offer = upsert_offer(
        supplier_id=supplier_id,
        product_id=product_id,
        unit_price=unit_price,
        moq=moq,
        is_active=is_active,
        discount_kind=discount_kind,
        discount_value=discount_value,
        discount_start=discount_start,
        discount_end=discount_end,
    )
    if on_hand is not None:
        current = stock_svc.get_balance(
            supplier_id=supplier_id, product_id=product_id, location_type="supplier", location_id=None
        )
        have = to_money(current.on_hand) if current is not None else Decimal("0")
        delta = to_money(on_hand) - have
        stock_svc.manual_adjust(
            supplier_id=supplier_id,
            product_id=product_id,
            location_type="supplier",
            location_id=None,
            delta=delta,
            reorder_point=reorder_point,
        )
    return {"offer": serialize_own(offer)}

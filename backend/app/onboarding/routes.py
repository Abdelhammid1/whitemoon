"""Onboarding «كيف أبدأ؟» checklist (T-18).

Returns the signed-in user's role-based setup tasks, each with `done` computed
from real system data where a clean signal exists. Tasks whose completion can't
be detected server-side (kind='ack') are acknowledged client-side.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func, select

from ..accounting.models import Account, BankReceipt, Period
from ..commerce.models import Cart, CartItem, Order
from ..extensions import db
from ..identity.models import CustomerProfile, SupplierProfile, TotpSecret, User
from ..inventory.models import Category, Product, StockBalance, SupplierOffer
from ..logistics.models import DeliverySlot, Shipment
from ..pos.models import PosSale
from ..sales.models import CreditTierSetting, CustomerCreditTier, PaymentApproval

bp = Blueprint("onboarding", __name__, url_prefix="/onboarding")


def _uid() -> int:
    return int(get_jwt_identity())


def _exists(model: Any, *where: Any) -> bool:
    stmt = select(func.count()).select_from(model)
    for w in where:
        stmt = stmt.where(w)
    return int(db.session.execute(stmt).scalar_one()) > 0


def _task(key: str, label: str, to: str, done: bool, kind: str = "auto") -> dict[str, Any]:
    return {"key": key, "label": label, "to": to, "done": bool(done), "kind": kind}


def _admin(uid: int) -> list[dict[str, Any]]:
    return [
        _task("secure", "تأمين الحساب وتفعيل التحقق الثنائي", "/2fa", _exists(TotpSecret, TotpSecret.user_id == uid)),
        _task("categories", "إضافة فئات المنتجات", "/inventory/categories", _exists(Category)),
        _task("accounts", "تهيئة دليل الحسابات", "/accounting/chart", _exists(Account)),
        _task("period", "فتح الفترة المالية", "/accounting/periods", _exists(Period, Period.is_closed.is_(False))),
        _task("tiers", "ضبط سقوف التصنيف الائتماني", "/credit/tiers", _exists(CreditTierSetting)),
        _task("team", "إضافة الموظفين والوكلاء", "/admin/users", _exists(User, User.kind.in_(("staff", "agent", "branch")))),
        _task("suppliers", "اعتماد الموردين", "/admin/suppliers/pending", _exists(SupplierProfile, SupplierProfile.approval_status == "approved")),
        _task("slots", "فتح مواعيد التوصيل", "/logistics", _exists(DeliverySlot)),
        _task("eta", "ضبط كود ETA للأصناف", "/compliance", _exists(Product, Product.eta_code.is_not(None))),
    ]


def _staff(uid: int) -> list[dict[str, Any]]:
    return [
        _task("secure", "تأمين الحساب وتفعيل التحقق الثنائي", "/2fa", _exists(TotpSecret, TotpSecret.user_id == uid)),
        _task("perms", "التعرّف على صلاحياتك", "/", False, kind="ack"),
        _task("collection", "تسجيل أول تحصيل", "/credit/payments", _exists(PaymentApproval)),
        _task("receipt", "رفع أول إيصال", "/accounting/receipts", _exists(BankReceipt)),
    ]


def _customer(user: User) -> list[dict[str, Any]]:
    uid = user.id
    has_cart = _exists(CartItem, CartItem.cart_id.in_(select(Cart.id).where(Cart.customer_id == uid)))
    has_order = _exists(Order, Order.customer_id == uid)
    has_shipment = _exists(Shipment, Shipment.order_id.in_(select(Order.id).where(Order.customer_id == uid)))
    profile = db.session.get(CustomerProfile, uid)
    return [
        _task("phone", "تأكيد رقم الهاتف", "/", user.phone_verified_at is not None or user.status == "active"),
        _task("profile", "تعبئة بيانات المتجر والعنوان", "/", bool(profile and profile.geo_area)),
        _task("browse", "تصفّح الكتالوج وإضافة أول منتج للسلة", "/catalog", has_cart or has_order),
        _task("tier", "فهم سقفك وتصنيفك الائتماني", "/orders", _exists(CustomerCreditTier, CustomerCreditTier.customer_id == uid)),
        _task("slot", "حجز موعد توصيل", "/orders", has_shipment),
    ]


def _supplier(uid: int) -> list[dict[str, Any]]:
    profile = db.session.get(SupplierProfile, uid)
    docs_done = bool(profile and profile.commercial_register_no and profile.tax_card_no)
    approved = bool(profile and profile.approval_status == "approved")
    return [
        _task("docs", "استكمال بيانات الشركة والوثائق", "/", docs_done),
        _task("approval", "اعتماد الحساب", "/", approved, kind="ack"),
        _task("offers", "إضافة العروض والأسعار", "/inventory/offers", _exists(SupplierOffer, SupplierOffer.supplier_id == uid)),
        _task("stock", "تحديث المخزون وحد إعادة الطلب", "/inventory/stock", _exists(StockBalance, StockBalance.supplier_id == uid, StockBalance.reorder_point.is_not(None))),
        _task("moq", "ضبط الحد الأدنى للطلب", "/inventory/offers", _exists(SupplierOffer, SupplierOffer.supplier_id == uid, SupplierOffer.moq > 0)),
    ]


def _agent(uid: int) -> list[dict[str, Any]]:
    return [
        _task("secure", "تفعيل التحقق الثنائي", "/2fa", _exists(TotpSecret, TotpSecret.user_id == uid)),
        _task("scope", "معرفة نطاقك ونسبة عمولتك", "/", False, kind="ack"),
        _task("sale", "تنفيذ أول بيع", "/pos", _exists(PosSale, PosSale.cashier_id == uid)),
        _task("track", "متابعة مبيعاتي", "/pos/sales", _exists(PosSale, PosSale.cashier_id == uid)),
    ]


@bp.get("/checklist")
@jwt_required()
def checklist():
    user = db.session.get(User, _uid())
    if user is None:
        return jsonify({"role": None, "tasks": [], "done_count": 0, "total": 0})
    kind = user.kind
    if kind in ("admin",):
        tasks = _admin(user.id)
    elif kind == "staff":
        tasks = _staff(user.id)
    elif kind == "customer":
        tasks = _customer(user)
    elif kind == "supplier":
        tasks = _supplier(user.id)
    elif kind in ("agent", "branch"):
        tasks = _agent(user.id)
    else:
        tasks = []
    done = sum(1 for t in tasks if t["done"])
    return jsonify({"role": kind, "tasks": tasks, "done_count": done, "total": len(tasks)})

"""Rich Arabic DEV mock-data seed for White Moon (وايت مون).

Run from backend/ with the venv active:

    python scripts/seed_mock.py

This populates realistic, Arabic-first demo data on top of the base seed
(RBAC roles, bootstrap admin, 72 chart-of-accounts). It is IDEMPOTENT: the
catalog/identity layer is get-or-create, and the transactional layer (orders,
dues, POS, production, logistics, …) only runs once (skipped if any order
already exists), so re-running never duplicates or crashes.

It prefers the domain SERVICE functions (checkout, credit, offers, stock,
partners, POS, production, logistics, chat) so the demo data respects the
same invariants the API enforces. All money is Decimal/EGP.

NOTE (domain constraint): the auto journal map only posts food/clothing
categories, so every money-posting flow (orders, POS, production) uses
food/clothing products on purpose. Products still span all 9 categories.
"""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Make `app` importable when invoked as a script.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

# The printout contains Arabic; force UTF-8 so a cp1252 Windows console
# doesn't crash on it.
try:  # pragma: no cover - console-dependent
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from sqlalchemy import select  # noqa: E402

# ----- models
from app.identity.models import (  # noqa: E402
    CustomerProfile,
    Role,
    SupplierProfile,
    User,
    UserRole,
)
from app.inventory.models import SupplierOffer  # noqa: E402
from app.commerce.models import Order  # noqa: E402
from app.sales.models import CustomerDue  # noqa: E402
from app.accounting.models import BankReceipt  # noqa: E402

# ----- services
from app.identity.services import passwords, rbac  # noqa: E402
from app.identity.services import supplier_approval  # noqa: E402
from app.inventory.services import offers as offers_svc  # noqa: E402
from app.inventory.services import products as products_svc  # noqa: E402
from app.inventory.services import reorder as reorder_svc  # noqa: E402
from app.inventory.services import stock as stock_svc  # noqa: E402
from app.commerce.services import cart as cart_svc  # noqa: E402
from app.commerce.services import orders as orders_svc  # noqa: E402
from app.commerce.services import rfq as rfq_svc  # noqa: E402
from app.sales.services import credit as credit_svc  # noqa: E402
from app.sales.services import escalation as escalation_svc  # noqa: E402
from app.sales.services import payments as payments_svc  # noqa: E402
from app.partners.services import partners as partners_svc  # noqa: E402
from app.production.services import production as production_svc  # noqa: E402
from app.pos.services import pos as pos_svc  # noqa: E402
from app.logistics.services import logistics as logistics_svc  # noqa: E402
from app.comm.services import chat as chat_svc  # noqa: E402
from app.notifications.services import notify as notify_svc  # noqa: E402

DEMO_PASSWORD = "WhiteMoon#2026"
MARKER_EMAIL = "hussieni.market@wm.eg"


def D(x) -> Decimal:  # noqa: N802 - short money helper
    return Decimal(str(x))


def _admin_id() -> int:
    stmt = select(User.id).join(UserRole).join(Role).where(Role.code == "admin.high")
    return int(db.session.execute(stmt).scalar_one())


# ---------------------------------------------------------------- identity


def _get_user_by_email(email: str) -> User | None:
    return db.session.execute(select(User).where(User.email == email)).scalar_one_or_none()


def ensure_customer(*, email: str, phone: str, display_name: str, geo_area: str,
                    created_days_ago: int = 0) -> User:
    user = _get_user_by_email(email)
    if user is not None:
        return user
    user = User(
        email=email, phone=phone,
        password_hash=passwords.hash_password(DEMO_PASSWORD),
        kind="customer", status="active", locale="ar",
        activated_at=datetime.now(UTC), email_verified_at=datetime.now(UTC),
    )
    if created_days_ago:
        user.created_at = datetime.now(UTC) - timedelta(days=created_days_ago)
    db.session.add(user)
    db.session.flush()
    db.session.add(CustomerProfile(user_id=user.id, display_name=display_name, geo_area=geo_area))
    rbac.assign_role(user.id, "customer")
    db.session.commit()
    return user


def ensure_supplier(*, email: str, phone: str, legal_name: str, cr_no: str, tax_no: str,
                    national_id: str, approved: bool, min_order_value: Decimal) -> User:
    user = _get_user_by_email(email)
    if user is None:
        user = User(
            email=email, phone=phone,
            password_hash=passwords.hash_password(DEMO_PASSWORD),
            kind="supplier", status="pending", locale="ar",
            email_verified_at=datetime.now(UTC),
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(SupplierProfile(
            user_id=user.id, legal_name=legal_name, commercial_register_no=cr_no,
            tax_card_no=tax_no, national_id=national_id, min_order_value=min_order_value,
            approval_status="pending",
        ))
        rbac.assign_role(user.id, "supplier")
        db.session.commit()
    if approved:
        prof = db.session.get(SupplierProfile, user.id)
        if prof is not None and prof.approval_status != "approved":
            supplier_approval.approve(admin_user_id=_admin_id(), user_id=user.id)
    return user


def ensure_staff(*, email: str, phone: str) -> User:
    user = _get_user_by_email(email)
    if user is not None:
        return user
    user = User(
        email=email, phone=phone,
        password_hash=passwords.hash_password(DEMO_PASSWORD),
        kind="staff", status="active", locale="ar",
        activated_at=datetime.now(UTC), email_verified_at=datetime.now(UTC),
    )
    db.session.add(user)
    db.session.flush()
    rbac.assign_role(user.id, "staff")
    db.session.commit()
    return user


def ensure_partner(*, email: str, phone: str, type_: str, display_name: str, geo_scope: str,
                   earns_commission: bool = False, commission_rate_pct: Decimal = D(0),
                   earns_investment_return: bool = False,
                   investment_return_rate_pct: Decimal = D(0)) -> User:
    user = _get_user_by_email(email)
    if user is not None:
        return user
    partners_svc.create_partner(
        type_=type_, display_name=display_name, geo_scope=geo_scope,
        phone=phone, email=email, password=DEMO_PASSWORD,
        earns_commission=earns_commission, commission_rate_pct=commission_rate_pct,
        earns_investment_return=earns_investment_return,
        investment_return_rate_pct=investment_return_rate_pct,
        actor_user_id=_admin_id(),
    )
    created = _get_user_by_email(email)
    assert created is not None  # just created above
    return created


# ---------------------------------------------------------------- inventory


def ensure_product(*, sku: str, name_ar: str, category: str, unit: str = "piece",
                   name_en: str | None = None, subcategory: str | None = None,
                   brand: str | None = None, food_expiry_tracked: bool = False,
                   variants: list[tuple[str, str, str]] | None = None):
    existing = db.session.execute(
        select(products_svc.Product).where(products_svc.Product.sku == sku)
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    p = products_svc.create_product(
        sku=sku, name_ar=name_ar, category=category, unit=unit, name_en=name_en,
        subcategory=subcategory, brand=brand, food_expiry_tracked=food_expiry_tracked,
        created_by=_admin_id(),
    )
    for vsku, size, color in (variants or []):
        products_svc.add_variant(product_id=p.id, sku=vsku, barcode=None, size=size, color=color)
    return p


def ensure_offer(*, supplier_id: int, product_id: int, unit_price: Decimal, moq: Decimal):
    existing = db.session.execute(
        select(SupplierOffer).where(
            SupplierOffer.supplier_id == supplier_id,
            SupplierOffer.product_id == product_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    return offers_svc.upsert_offer(
        supplier_id=supplier_id, product_id=product_id,
        unit_price=unit_price, moq=moq, is_active=True,
    )


def ensure_stock(*, supplier_id: int, product_id: int, on_hand: Decimal,
                 reorder_point: Decimal) -> None:
    bal = stock_svc.get_balance(
        supplier_id=supplier_id, product_id=product_id,
        location_type="supplier", location_id=None,
    )
    if bal is not None:
        return
    stock_svc.manual_adjust(
        supplier_id=supplier_id, product_id=product_id,
        location_type="supplier", location_id=None,
        delta=on_hand, reorder_point=reorder_point,
    )


# ---------------------------------------------------------------- credit helpers


def add_settled_due(cid: int, *, amount: Decimal, due_days_ago: int, days_late: int,
                    defaulted: bool = False) -> None:
    due_date = date.today() - timedelta(days=due_days_ago)
    paid_date = due_date + timedelta(days=days_late)
    db.session.add(CustomerDue(
        customer_id=cid, order_id=None, amount=D(amount),
        due_date=due_date, paid_date=paid_date, days_late=days_late,
        status="defaulted" if defaulted else "paid",
    ))


def add_open_due(cid: int, *, amount: Decimal, overdue_days: int) -> None:
    due_date = date.today() - timedelta(days=overdue_days)
    db.session.add(CustomerDue(
        customer_id=cid, order_id=None, amount=D(amount),
        due_date=due_date, status="open",
    ))


# ---------------------------------------------------------------- main seed


def seed() -> dict:
    admin_id = _admin_id()

    # ---- Suppliers (3 approved + 1 pending)
    sup_nile = ensure_supplier(
        email="nile.foods@wm.eg", phone="+201000100001",
        legal_name="مخازن النيل للمواد الغذائية", cr_no="CR-100001",
        tax_no="TAX-100001", national_id="29001011200011",
        approved=True, min_order_value=D(500),
    )
    sup_east = ensure_supplier(
        email="east.fashion@wm.eg", phone="+201000100002",
        legal_name="أزياء الشرق للملابس", cr_no="CR-100002",
        tax_no="TAX-100002", national_id="29001011200012",
        approved=True, min_order_value=D(300),
    )
    sup_tech = ensure_supplier(
        email="modern.tech@wm.eg", phone="+201000100003",
        legal_name="التقنية الحديثة للإلكترونيات", cr_no="CR-100003",
        tax_no="TAX-100003", national_id="29001011200013",
        approved=True, min_order_value=D(0),
    )
    ensure_supplier(
        email="alamal.trade@wm.eg", phone="+201000100004",
        legal_name="مؤسسة الأمل للتجارة", cr_no="CR-100004",
        tax_no="TAX-100004", national_id="29001011200014",
        approved=False, min_order_value=D(0),
    )

    # ---- Customers
    c_hussieni = ensure_customer(email=MARKER_EMAIL, phone="+201000200001",
                                 display_name="سوبر ماركت الحسيني", geo_area="القاهرة",
                                 created_days_ago=400)
    c_noor = ensure_customer(email="alnoor.grocery@wm.eg", phone="+201000200002",
                             display_name="بقالة النور", geo_area="الجيزة",
                             created_days_ago=400)
    c_baraka = ensure_customer(email="albaraka.stores@wm.eg", phone="+201000200003",
                               display_name="محلات البركة", geo_area="الإسكندرية",
                               created_days_ago=400)
    c_aseel = ensure_customer(email="alaseel.rest@wm.eg", phone="+201000200004",
                              display_name="مطعم الأصيل", geo_area="المنصورة",
                              created_days_ago=400)
    c_wafa = ensure_customer(email="alwafa.shop@wm.eg", phone="+201000200005",
                             display_name="متجر الوفاء", geo_area="أسيوط",
                             created_days_ago=8)
    c_salam = ensure_customer(email="alsalam.mini@wm.eg", phone="+201000200006",
                              display_name="ميني ماركت السلام", geo_area="القاهرة",
                              created_days_ago=120)

    # ---- Agents + branches
    ag_cairo = ensure_partner(email="cairo.agent@wm.eg", phone="+201000300001",
                              type_="agent", display_name="وكيل القاهرة الكبرى",
                              geo_scope="القاهرة", earns_commission=True,
                              commission_rate_pct=D("2.50"), earns_investment_return=True,
                              investment_return_rate_pct=D("1.00"))
    ag_delta = ensure_partner(email="delta.agent@wm.eg", phone="+201000300002",
                              type_="agent", display_name="وكيل الدلتا",
                              geo_scope="المنصورة", earns_commission=True,
                              commission_rate_pct=D("3.00"))
    br_nasr = ensure_partner(email="nasrcity.branch@wm.eg", phone="+201000300003",
                             type_="branch", display_name="فرع مدينة نصر", geo_scope="القاهرة")
    ensure_partner(email="smouha.branch@wm.eg", phone="+201000300004",
                   type_="branch", display_name="فرع سموحة", geo_scope="الإسكندرية")

    # ---- Staff
    staff_sales = ensure_staff(email="sales.staff@wm.eg", phone="+201000400001")
    ensure_staff(email="wh.staff@wm.eg", phone="+201000400002")

    # ---- Products (20 across 9 categories)
    p = {}
    p["rice"] = ensure_product(sku="WM-F-001", name_ar="أرز مصري فاخر", category="food",
                               unit="kg", brand="النيل", food_expiry_tracked=True)
    p["sugar"] = ensure_product(sku="WM-F-002", name_ar="سكر أبيض ناعم", category="food", unit="kg")
    p["oil"] = ensure_product(sku="WM-F-003", name_ar="زيت عباد الشمس", category="food",
                              unit="piece", brand="عافية")
    p["tea"] = ensure_product(sku="WM-F-004", name_ar="شاي العروسة", category="food", unit="piece")
    p["pasta"] = ensure_product(sku="WM-F-005", name_ar="مكرونة إيطالية", category="food", unit="piece")
    p["shirt"] = ensure_product(sku="WM-C-001", name_ar="قميص قطني رجالي", category="clothing",
                                brand="الشرق", subcategory="رجالي",
                                variants=[("WM-C-001-S-W", "S", "أبيض"),
                                          ("WM-C-001-M-W", "M", "أبيض"),
                                          ("WM-C-001-L-B", "L", "أزرق")])
    p["dress"] = ensure_product(sku="WM-C-002", name_ar="فستان صيفي حريمي", category="clothing",
                                subcategory="حريمي",
                                variants=[("WM-C-002-M-R", "M", "أحمر"),
                                          ("WM-C-002-L-R", "L", "أحمر")])
    p["jeans"] = ensure_product(sku="WM-C-003", name_ar="بنطلون جينز", category="clothing",
                                variants=[("WM-C-003-32", "32", "كحلي"),
                                          ("WM-C-003-34", "34", "كحلي")])
    p["phone"] = ensure_product(sku="WM-E-001", name_ar="هاتف ذكي", category="electronics",
                                brand="سامسونج")
    p["buds"] = ensure_product(sku="WM-E-002", name_ar="سماعات بلوتوث", category="electronics")
    p["pots"] = ensure_product(sku="WM-H-001", name_ar="طقم حلل تيفال", category="home")
    p["vacuum"] = ensure_product(sku="WM-H-002", name_ar="مكنسة كهربائية", category="home")
    p["cream"] = ensure_product(sku="WM-B-001", name_ar="كريم ترطيب للبشرة", category="beauty")
    p["shampoo"] = ensure_product(sku="WM-B-002", name_ar="شامبو للشعر", category="beauty")
    p["cement"] = ensure_product(sku="WM-K-001", name_ar="أسمنت بورتلاندي", category="construction",
                                 unit="bag")
    p["brick"] = ensure_product(sku="WM-K-002", name_ar="طوب أحمر", category="construction")
    p["notebook"] = ensure_product(sku="WM-S-001", name_ar="دفتر 100 ورقة", category="stationery")
    p["pens"] = ensure_product(sku="WM-S-002", name_ar="علبة أقلام جاف", category="stationery")
    p["motoroil"] = ensure_product(sku="WM-A-001", name_ar="زيت محرك 5W-30", category="automotive",
                                   unit="piece")
    p["cleaner"] = ensure_product(sku="WM-O-001", name_ar="منظف أرضيات", category="other")

    # ---- Offers: multiple suppliers per product (varying price/moq)
    # nile = primary food/general; east = clothing + second source; tech = electronics/home
    offer_plan = [
        # product, [(supplier, price, moq), ...]
        ("rice", [(sup_nile, D("28.50"), D(5)), (sup_east, D("29.75"), D(10))]),
        ("sugar", [(sup_nile, D("24.00"), D(5)), (sup_tech, D("24.90"), D(2))]),
        ("oil", [(sup_nile, D("62.00"), D(1)), (sup_east, D("63.50"), D(1))]),
        ("tea", [(sup_nile, D("45.00"), D(1))]),
        ("pasta", [(sup_nile, D("12.75"), D(10)), (sup_tech, D("13.20"), D(6))]),
        ("shirt", [(sup_east, D("185.00"), D(1)), (sup_nile, D("199.00"), D(1))]),
        ("dress", [(sup_east, D("320.00"), D(1))]),
        ("jeans", [(sup_east, D("275.00"), D(1)), (sup_tech, D("289.00"), D(1))]),
        ("phone", [(sup_tech, D("8500.00"), D(1))]),
        ("buds", [(sup_tech, D("450.00"), D(1)), (sup_east, D("469.00"), D(1))]),
        ("pots", [(sup_tech, D("1250.00"), D(1))]),
        ("vacuum", [(sup_tech, D("2100.00"), D(1))]),
        ("cream", [(sup_nile, D("85.00"), D(1))]),
        ("shampoo", [(sup_nile, D("55.00"), D(1)), (sup_east, D("57.50"), D(1))]),
        ("cement", [(sup_tech, D("95.00"), D(10))]),
        ("brick", [(sup_tech, D("2.50"), D(100))]),
        ("notebook", [(sup_nile, D("15.00"), D(5))]),
        ("pens", [(sup_nile, D("22.00"), D(2))]),
        ("motoroil", [(sup_tech, D("210.00"), D(1))]),
        ("cleaner", [(sup_nile, D("33.00"), D(1))]),
    ]
    offer_by = {}  # (prod_key, supplier_id) -> offer
    for key, rows in offer_plan:
        for sup, price, moq in rows:
            o = ensure_offer(supplier_id=sup.id, product_id=p[key].id, unit_price=price, moq=moq)
            offer_by[(key, sup.id)] = o

    # ---- Stock balances (some deliberately LOW to trigger reorder alerts)
    stock_plan = [
        (sup_nile, "rice", D(1200), D(200)),
        (sup_nile, "sugar", D(300), D(100)),
        (sup_nile, "oil", D(40), D(50)),       # LOW
        (sup_nile, "tea", D(500), D(80)),
        (sup_nile, "pasta", D(900), D(150)),
        (sup_nile, "cream", D(60), D(20)),
        (sup_nile, "shampoo", D(15), D(40)),   # LOW
        (sup_east, "shirt", D(250), D(60)),
        (sup_east, "dress", D(18), D(25)),     # LOW
        (sup_east, "jeans", D(140), D(40)),
        (sup_tech, "phone", D(35), D(10)),
        (sup_tech, "buds", D(120), D(30)),
        (sup_tech, "pots", D(22), D(15)),
        (sup_tech, "vacuum", D(8), D(10)),     # LOW
    ]
    for sup, key, on_hand, rop in stock_plan:
        ensure_stock(supplier_id=sup.id, product_id=p[key].id, on_hand=on_hand, reorder_point=rop)

    # Open reorder alerts for the low balances.
    reorder_svc.check()

    ids = {
        "admin": admin_id,
        "sup_nile": sup_nile.id, "sup_east": sup_east.id, "sup_tech": sup_tech.id,
        "c_hussieni": c_hussieni.id, "c_noor": c_noor.id, "c_baraka": c_baraka.id,
        "c_aseel": c_aseel.id, "c_wafa": c_wafa.id, "c_salam": c_salam.id,
        "ag_cairo": ag_cairo.id, "ag_delta": ag_delta.id, "br_nasr": br_nasr.id,
        "staff_sales": staff_sales.id,
    }

    # ========================================================= Phase B (one-shot)
    orders_exist = db.session.query(Order.id).first() is not None
    if orders_exist:
        print("Phase B (transactional demo) already present — skipped.")
        return ids

    # ---- Credit history + tiers + escalation
    # c_hussieni → GREEN (long clean history)
    for i in range(5):
        add_settled_due(c_hussieni.id, amount=D(20000 + i * 1000), due_days_ago=300 - i * 40, days_late=0)
    # c_noor → YELLOW (mostly on-time, one late) + a 10-day overdue (L2)
    for i in range(4):
        add_settled_due(c_noor.id, amount=D(8000), due_days_ago=250 - i * 40, days_late=0)
    add_settled_due(c_noor.id, amount=D(8000), due_days_ago=90, days_late=18)
    add_open_due(c_noor.id, amount=D(12000), overdue_days=10)
    # c_baraka → RED (a default in history) + a 50-day overdue (L4 freeze)
    for i in range(2):
        add_settled_due(c_baraka.id, amount=D(15000), due_days_ago=260 - i * 50, days_late=0)
    add_settled_due(c_baraka.id, amount=D(15000), due_days_ago=150, days_late=120, defaulted=True)
    add_open_due(c_baraka.id, amount=D(30000), overdue_days=50)
    # c_aseel → GREEN base downgraded to YELLOW via L3 escalation floor (20-day overdue)
    for i in range(5):
        add_settled_due(c_aseel.id, amount=D(10000), due_days_ago=280 - i * 45, days_late=0)
    add_open_due(c_aseel.id, amount=D(18000), overdue_days=20)
    # c_salam → GREEN (clean, younger) — used for orders
    for i in range(3):
        add_settled_due(c_salam.id, amount=D(14000), due_days_ago=100 - i * 25, days_late=0)
    db.session.commit()

    for cid in (c_hussieni.id, c_noor.id, c_baraka.id, c_aseel.id, c_wafa.id, c_salam.id):
        credit_svc.recompute(cid)
    db.session.commit()

    # Escalation events (dunning board) for the overdue customers.
    for cid in (c_noor.id, c_baraka.id, c_aseel.id):
        escalation_svc.run_for_customer(cid)

    # A manual credit-limit override on the green flagship customer (US-5.2).
    credit_svc.set_override(customer_id=c_hussieni.id, credit_limit=D(750000),
                            reason="عميل مميز بسجل ممتاز — رفع السقف", set_by=admin_id)

    # ---- Commerce: carts → orders (cash + deferred), mixed statuses
    # Order 1: c_salam cash (food) → fulfilled
    cart_svc.add_item(customer_id=c_salam.id, offer_id=offer_by[("rice", sup_nile.id)].id, qty=D(50))
    cart_svc.add_item(customer_id=c_salam.id, offer_id=offer_by[("sugar", sup_nile.id)].id, qty=D(30))
    cart_svc.add_item(customer_id=c_salam.id, offer_id=offer_by[("oil", sup_nile.id)].id, qty=D(12))
    order1 = orders_svc.checkout(customer_id=c_salam.id, payment_mode="cash")
    order1.status = "fulfilled"
    db.session.commit()

    # Order 2: c_hussieni deferred (food + clothing) → confirmed
    cart_svc.add_item(customer_id=c_hussieni.id, offer_id=offer_by[("pasta", sup_nile.id)].id, qty=D(100))
    cart_svc.add_item(customer_id=c_hussieni.id, offer_id=offer_by[("shirt", sup_east.id)].id, qty=D(20))
    cart_svc.add_item(customer_id=c_hussieni.id, offer_id=offer_by[("tea", sup_nile.id)].id, qty=D(40))
    order2 = orders_svc.checkout(customer_id=c_hussieni.id, payment_mode="deferred")
    order2.status = "confirmed"
    db.session.commit()

    # Order 3: c_wafa cash (clothing) → pending
    cart_svc.add_item(customer_id=c_wafa.id, offer_id=offer_by[("jeans", sup_east.id)].id, qty=D(10))
    cart_svc.add_item(customer_id=c_wafa.id, offer_id=offer_by[("dress", sup_east.id)].id, qty=D(6))
    order3 = orders_svc.checkout(customer_id=c_wafa.id, payment_mode="cash")

    # One cart left ACTIVE (not checked out) for the cart screen.
    cart_svc.add_item(customer_id=c_noor.id, offer_id=offer_by[("rice", sup_nile.id)].id, qty=D(20))
    cart_svc.add_item(customer_id=c_noor.id, offer_id=offer_by[("shampoo", sup_nile.id)].id, qty=D(8))

    # ---- RFQs with supplier offers
    rfq1 = rfq_svc.create_rfq(initiator_user_id=c_hussieni.id, initiator_type="customer",
                              product_id=p["phone"].id, qty=D(15),
                              deadline=date.today() + timedelta(days=7),
                              qualification_requirements="ضمان سنتين وفاتورة ضريبية")
    rfq_svc.submit_offer(rfq_id=rfq1.id, supplier_id=sup_tech.id, unit_price=D("8300.00"), moq=D(10))
    rfq2 = rfq_svc.create_rfq(initiator_user_id=c_salam.id, initiator_type="customer",
                              product_id=p["rice"].id, qty=D(500),
                              deadline=date.today() + timedelta(days=5),
                              qualification_requirements="تسليم خلال 48 ساعة")
    rfq_svc.submit_offer(rfq_id=rfq2.id, supplier_id=sup_nile.id, unit_price=D("27.90"), moq=D(100))
    rfq_svc.submit_offer(rfq_id=rfq2.id, supplier_id=sup_east.id, unit_price=D("28.40"), moq=D(50))

    # ---- Payments: settle one due + a pending collection awaiting approval
    extra_due = credit_svc.record_due(customer_id=c_salam.id, order_id=None, amount=D(14000),
                                      due_date=date.today())
    db.session.commit()
    # Agent (القاهرة scope) collects from c_salam (القاهرة) — pending one approval.
    payments_svc.collect_payment(customer_id=c_salam.id, due_id=extra_due.id, amount=D(14000),
                                 paid_on=date.today(), collected_by=ag_cairo.id)
    # Another standalone pending collection (no due link).
    payments_svc.collect_payment(customer_id=c_hussieni.id, due_id=None, amount=D(5000),
                                 paid_on=date.today(), collected_by=ag_cairo.id)

    # ---- Accounting: bank receipts (pending + matched) + deferred terms
    db.session.add(BankReceipt(uploaded_by=c_hussieni.id, image_s3_key="receipts/demo-pending-1.jpg",
                               status="pending"))
    db.session.add(BankReceipt(uploaded_by=c_salam.id, image_s3_key="receipts/demo-matched-1.jpg",
                               ocr_amount=D("1905.00"), ocr_reference="TRX-558021",
                               status="matched", matched_order_id=order1.id))
    db.session.commit()
    # (deferred_terms row was created automatically by order2's deferred checkout.)

    # ---- Partners: deposits, current-account ledger, accrual
    partners_svc.record_deposit(partner_id=ag_cairo.id, amount=D(50000), deposit_date=date.today(),
                                recovery_conditions="يُرد عند إنهاء التعاقد وتسوية الذمم",
                                posted_by=admin_id)
    partners_svc.record_deposit(partner_id=ag_delta.id, amount=D(35000), deposit_date=date.today(),
                                recovery_conditions="تأمين تشغيلي قابل للاسترداد", posted_by=admin_id)
    partners_svc.record_ledger_entry(partner_id=ag_cairo.id, kind="payment_received",
                                     amount=D(12000), direction=None,
                                     note="تحصيل نقدي مورّد من الوكيل", posted_by=admin_id)
    partners_svc.record_ledger_entry(partner_id=br_nasr.id, kind="manual", amount=D(2500),
                                     direction=1, note="تسوية فروق جرد الفرع", posted_by=admin_id)
    # Attribute the confirmed order to the Cairo agent and accrue commission.
    partners_svc.attribute_order(order_id=order2.id, partner_id=ag_cairo.id, actor_user_id=admin_id)
    today = date.today()
    partners_svc.compute_accrual(partner_id=ag_cairo.id, kind="commission",
                                 year=today.year, month=today.month, posted_by=admin_id)

    # ---- Production: one completed MO (rice → pasta) + one left in-progress
    mo1 = production_svc.create_mo(
        owner_id=sup_nile.id, output_product_id=p["pasta"].id, output_qty=D(200),
        materials=[production_svc.MaterialInput(product_id=p["rice"].id, qty=D(50), unit_cost=D("28.50"))],
        stages=["تجهيز الخامات", "التصنيع", "التعبئة والتغليف"],
        actor_user_id=admin_id,
    )
    for _ in range(3):
        production_svc.advance_stage(mo_id=mo1.id, actor_user_id=admin_id)
    production_svc.complete(mo_id=mo1.id, posted_by=admin_id)

    mo2 = production_svc.create_mo(
        owner_id=sup_nile.id, output_product_id=p["pasta"].id, output_qty=D(120),
        materials=[production_svc.MaterialInput(product_id=p["rice"].id, qty=D(30), unit_cost=D("28.50"))],
        stages=["تجهيز الخامات", "التصنيع", "التعبئة والتغليف"],
        actor_user_id=admin_id,
    )
    production_svc.advance_stage(mo_id=mo2.id, actor_user_id=admin_id)  # left in_progress

    # ---- POS: two sales then settle the batch
    pos_svc.create_sale(
        cashier_id=staff_sales.id, location_type="supplier", location_id=None,
        lines=[pos_svc.SaleLineInput(product_id=p["sugar"].id, supplier_id=sup_nile.id, qty=D(10)),
               pos_svc.SaleLineInput(product_id=p["tea"].id, supplier_id=sup_nile.id, qty=D(5))],
    )
    pos_svc.create_sale(
        cashier_id=staff_sales.id, location_type="supplier", location_id=None,
        lines=[pos_svc.SaleLineInput(product_id=p["shirt"].id, supplier_id=sup_east.id, qty=D(3))],
    )
    pos_svc.settle_batch(posted_by=staff_sales.id)

    # ---- Logistics: slot, shipment with legs, delivery with a shortage
    slot1 = logistics_svc.create_slot(slot_date=date.today() + timedelta(days=1),
                                      window="09:00-11:00", capacity=20)
    logistics_svc.create_slot(slot_date=date.today() + timedelta(days=1),
                              window="13:00-15:00", capacity=15)
    shipment = logistics_svc.book_slot(order_id=order1.id, slot_id=slot1.id,
                                       carrier_type="internal", actor_user_id=staff_sales.id)
    logistics_svc.add_leg(shipment_id=shipment.id, carrier_type="internal", carrier_ref="VAN-12",
                          from_label="مخزن النيل - القاهرة", to_label="مركز الفرز")
    logistics_svc.add_leg(shipment_id=shipment.id, carrier_type="external", carrier_ref="BOSTA-99",
                          from_label="مركز الفرز", to_label="ميني ماركت السلام")
    logistics_svc.update_status(shipment_id=shipment.id, status="shipped", actor_user_id=staff_sales.id)
    logistics_svc.update_status(shipment_id=shipment.id, status="in_transit", actor_user_id=staff_sales.id)
    logistics_svc.confirm_delivery(
        shipment_id=shipment.id, delivered_by=staff_sales.id,
        confirmation_code=shipment.confirmation_code,
        shortages=[logistics_svc.ShortageInput(product_id=p["oil"].id, qty=D(2),
                                               photo_url="shortages/oil-dented.jpg",
                                               note="عبوتان تالفتان عند التسليم")],
    )

    # ---- Comm: a mediated conversation (one normal msg + one blocked by filter)
    conv = chat_svc.start_conversation(customer_id=c_hussieni.id, supplier_id=sup_nile.id,
                                       order_id=order2.id, subject="استفسار عن موعد الشحن")
    chat_svc.send_message(conversation_id=conv.id, sender_id=c_hussieni.id,
                          body="السلام عليكم، متى يتم شحن الطلب؟")
    chat_svc.send_message(conversation_id=conv.id, sender_id=sup_nile.id,
                          body="تواصل معي على رقمي ٠١٠١٢٣٤٥٦٧٨ لتنسيق التسليم")  # blocked

    # ---- Notifications (a few beyond the supplier-approval ones already sent)
    notify_svc.notify(user_id=c_salam.id, title="تم تأكيد طلبك",
                      body=f"تم استلام طلبك رقم {order1.number} وجارٍ التجهيز.",
                      type_="order", channel="in_app")
    notify_svc.notify(user_id=c_hussieni.id, title="طلبك الآجل قيد المراجعة",
                      body=f"طلبك {order2.number} بالبيع الآجل تم اعتماده.",
                      type_="order", channel="in_app")
    notify_svc.notify(user_id=c_noor.id, title="تنبيه تأخر سداد",
                      body="لديك ذمة متأخرة — يُرجى السداد لتفادي تصعيد التحصيل.",
                      type_="credit", channel="in_app")

    ids["order1"] = order1.id
    ids["order2"] = order2.id
    ids["order3"] = order3.id
    return ids


def main() -> None:
    app = create_app()
    with app.app_context():
        ids = seed()
        print("\n" + "=" * 64)
        print("White Moon mock seed complete.")
        print("=" * 64)
        print(f"All demo accounts share the password: {DEMO_PASSWORD}")
        print("Log in via POST /auth/login with email + password.\n")
        print("Bootstrap admin (from base seed):")
        print("  admin@whitemoon.eg / ChangeMeNow!2026  (admin.high)\n")
        print("Suppliers:")
        print("  nile.foods@wm.eg     — مخازن النيل للمواد الغذائية   [approved]")
        print("  east.fashion@wm.eg   — أزياء الشرق للملابس           [approved]")
        print("  modern.tech@wm.eg    — التقنية الحديثة للإلكترونيات   [approved]")
        print("  alamal.trade@wm.eg   — مؤسسة الأمل للتجارة           [PENDING approval]\n")
        print("Customers (credit tier):")
        print("  hussieni.market@wm.eg — سوبر ماركت الحسيني   [green + override]")
        print("  alnoor.grocery@wm.eg  — بقالة النور          [yellow / L2 overdue]")
        print("  albaraka.stores@wm.eg — محلات البركة         [red / L4 frozen]")
        print("  alaseel.rest@wm.eg    — مطعم الأصيل          [L3 downgrade floor]")
        print("  alwafa.shop@wm.eg     — متجر الوفاء          [white / new]")
        print("  alsalam.mini@wm.eg    — ميني ماركت السلام    [green, has orders]\n")
        print("Agents / branches / staff:")
        print("  cairo.agent@wm.eg (وكيل القاهرة الكبرى), delta.agent@wm.eg (وكيل الدلتا)")
        print("  nasrcity.branch@wm.eg (فرع مدينة نصر), smouha.branch@wm.eg (فرع سموحة)")
        print("  sales.staff@wm.eg, wh.staff@wm.eg")
        print("  (agents/branches/staff require TOTP enrollment on first login)\n")
        print(f"key ids: {ids}")


if __name__ == "__main__":
    main()

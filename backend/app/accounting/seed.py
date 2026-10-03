"""Idempotent accounting seed.

Mirrors the signed/reviewed versions of:
- docs/02-chart-of-accounts.md  (review round 2 — 5281 commission expense,
                                 5290 investment-return expense, no 2121)
- docs/03-journal-map.md        (review round 2 — inventory.issued is
                                 location-aware; agent accruals hit 5281
                                 and 5290; two-step transfer via 9100)
"""

from __future__ import annotations

from sqlalchemy import select

from ..extensions import db
from .models import Account, EventJournalMap

# ---------------------------------------------------------------- Chart of accounts
# Order: parent before child. Non-postable = aggregator / branch of tree.
# fields: code, name_ar, name_en, type, parent, is_postable, category(optional)

COA: tuple[tuple[str, str, str, str, str | None, bool, str | None], ...] = (
    # 1xxx assets
    ("1000", "الأصول", "Assets", "asset", None, False, None),
    ("1100", "الأصول المتداولة", "Current Assets", "asset", "1000", False, None),
    ("1110", "النقدية والبنوك", "Cash & Banks", "asset", "1100", False, None),
    ("1111", "الصندوق الرئيسي", "Main Cash", "asset", "1110", True, None),
    ("1112", "البنوك — حسابات جارية", "Banks — Current", "asset", "1110", True, None),
    ("1120", "التحصيل المعلّق (OCR قيد المطابقة)", "OCR Pending Clearing", "asset", "1100", True, None),
    ("1130", "ذمم العملاء", "Customer Receivables", "asset", "1100", False, None),
    ("1131", "ذمم عملاء — نقدي", "Customer Receivables — Cash", "asset", "1130", True, None),
    ("1132", "ذمم عملاء — آجل", "Customer Receivables — Deferred", "asset", "1130", True, None),
    ("1140", "ذمم الوكلاء والفروع", "Channel Partner Receivables", "asset", "1100", False, None),
    ("1141", "ذمم الوكلاء — تحصيلات معلّقة", "Agents — Pending", "asset", "1140", True, None),
    ("1142", "ذمم الفروع — تحصيلات معلّقة", "Branches — Pending", "asset", "1140", True, None),
    ("1150", "المخزون", "Inventory", "asset", "1100", False, None),
    ("1151", "مخزون المنصة — غذائية", "Platform Stock — Food", "asset", "1150", True, "food"),
    ("1152", "مخزون المنصة — ملابس", "Platform Stock — Clothing", "asset", "1150", True, "clothing"),
    ("1153", "مخزون في عهدة الوكلاء/الفروع", "Stock at Channel Partners", "asset", "1150", True, None),
    ("1154", "مخزون في الطريق", "Stock in Transit", "asset", "1150", True, None),
    ("1160", "مصروفات مدفوعة مقدمًا", "Prepaid Expenses", "asset", "1100", True, None),
    ("1170", "عهد ومستحقات موظفين", "Staff Advances", "asset", "1100", True, None),
    ("1200", "الأصول الثابتة", "Fixed Assets", "asset", "1000", False, None),
    ("1210", "معدات ومكاتب", "Equipment & Office", "asset", "1200", True, None),
    ("1220", "مجمع الإهلاك — معدات ومكاتب", "Accum. Depr — Equipment", "contra", "1200", True, None),
    ("1230", "أصول غير ملموسة (برمجيات)", "Intangibles — Software", "asset", "1200", True, None),
    ("1240", "مجمع الإطفاء — أصول غير ملموسة", "Accum. Amort — Intangibles", "contra", "1200", True, None),

    # 2xxx liabilities
    ("2000", "الالتزامات", "Liabilities", "liability", None, False, None),
    ("2100", "الالتزامات قصيرة الأجل", "Current Liabilities", "liability", "2000", False, None),
    ("2110", "الدائنون — موردون", "Suppliers Payable", "liability", "2100", False, None),
    ("2111", "دائنون موردون — غذائية", "Suppliers Payable — Food", "liability", "2110", True, "food"),
    ("2112", "دائنون موردون — ملابس", "Suppliers Payable — Clothing", "liability", "2110", True, "clothing"),
    ("2120", "تأمينات الوكلاء", "Agent Deposits", "liability", "2100", True, None),
    ("2130", "عمولات مستحقة للوكلاء", "Agent Commissions Payable", "liability", "2100", True, None),
    ("2140", "عوائد استثمارية مستحقة للوكلاء", "Agent Investment Returns Payable", "liability", "2100", True, None),
    ("2150", "ضرائب مستحقة", "Taxes Payable", "liability", "2100", False, None),
    ("2151", "ضريبة قيمة مضافة مستحقة", "VAT Payable", "liability", "2150", True, None),
    ("2160", "مصروفات مستحقة", "Accrued Expenses", "liability", "2100", True, None),
    ("2170", "إيرادات مؤجلة", "Deferred Revenue", "liability", "2100", True, None),

    # 3xxx equity
    ("3000", "حقوق الملكية", "Equity", "equity", None, False, None),
    ("3100", "رأس المال المدفوع", "Paid-in Capital", "equity", "3000", True, None),
    ("3200", "الاحتياطيات", "Reserves", "equity", "3000", True, None),
    ("3300", "الأرباح المحتجزة", "Retained Earnings", "equity", "3000", True, None),
    ("3400", "أرباح/خسائر الفترة الجارية", "Current Period P/L", "equity", "3000", True, None),

    # 4xxx revenues
    ("4000", "الإيرادات", "Revenues", "revenue", None, False, None),
    ("4100", "إيرادات المبيعات", "Sales Revenue", "revenue", "4000", False, None),
    ("4110", "مبيعات — غذائية", "Sales — Food", "revenue", "4100", True, "food"),
    ("4120", "مبيعات — ملابس", "Sales — Clothing", "revenue", "4100", True, "clothing"),
    ("4130", "مبيعات نقطة البيع — غذائية", "POS Sales — Food", "revenue", "4100", True, "food"),
    ("4140", "مبيعات نقطة البيع — ملابس", "POS Sales — Clothing", "revenue", "4100", True, "clothing"),
    ("4200", "فروق التسعير الآجل", "Deferred Price Spread", "revenue", "4000", True, None),
    ("4300", "إيراد خصم استحقاق محتسب", "Early-Settlement Discount", "contra", "4000", True, None),
    ("4400", "إيرادات متنوعة", "Other Revenue", "revenue", "4000", True, None),

    # 5xxx expenses
    ("5000", "المصروفات", "Expenses", "expense", None, False, None),
    ("5100", "تكلفة المبيعات", "COGS", "expense", "5000", False, None),
    ("5110", "تكلفة المبيعات — غذائية", "COGS — Food", "expense", "5100", True, "food"),
    ("5120", "تكلفة المبيعات — ملابس", "COGS — Clothing", "expense", "5100", True, "clothing"),
    ("5200", "مصروفات التشغيل", "Operating Expenses", "expense", "5000", False, None),
    ("5210", "رواتب وأجور", "Salaries & Wages", "expense", "5200", True, None),
    ("5220", "إيجارات", "Rent", "expense", "5200", True, None),
    ("5230", "مصروفات تسويق", "Marketing", "expense", "5200", True, None),
    ("5240", "مصروفات شحن وتوصيل", "Shipping & Delivery", "expense", "5200", True, None),
    ("5250", "مصروفات بنكية ورسوم", "Bank Fees", "expense", "5200", True, None),
    ("5260", "إهلاك واستهلاك", "Depreciation & Amortization", "expense", "5200", True, None),
    ("5270", "مصروفات صيانة وبرمجيات", "Maintenance & Software", "expense", "5200", True, None),
    ("5280", "عمولات موردين/وسطاء خارجيين", "External Commissions", "expense", "5200", True, None),
    ("5281", "عمولة الوكلاء — مصروف", "Agent Commission Expense", "expense", "5200", True, None),
    ("5290", "عائد استثماري الوكلاء — مصروف", "Agent Investment Return Expense", "expense", "5200", True, None),
    ("5300", "خسائر وفروق تسوية", "Losses & Adjustments", "expense", "5000", False, None),
    ("5310", "خسائر نواقص ومرتجعات غير محمَّلة", "Unallocated Shortage Losses", "expense", "5300", True, None),

    # 9xxx clearing / suspense
    ("9000", "حسابات التسوية", "Clearing Accounts", "clearing", None, False, None),
    ("9100", "تحويلات بين المواقع — قيد التسوية", "Inter-Location Transfers Clearing", "clearing", "9000", True, None),
    ("9200", "مطابقة التحصيل OCR — قيد التسوية", "OCR Collection Clearing", "clearing", "9000", True, None),
    ("9300", "قيود نقطة البيع — قيد التجميع اليومي", "POS Daily Batch Clearing", "clearing", "9000", True, None),
    ("9900", "تسوية فتح/إقفال فترة", "Period Open/Close Clearing", "clearing", "9000", True, None),
)


# ---------------------------------------------------------------- Event → Journal map
# Mirrors docs/03-journal-map.md (review round 2).

# Each row: (event_type, step, side, account_code | None, rule_json, amount_source, description)
EVENT_MAP = (
    # 1 — order.placed.cash
    (
        "order.placed.cash", 1, "debit", "1131", None, "amount",
        "ذمم العملاء — نقدي",
    ),
    (
        "order.placed.cash", 2, "credit", None,
        {"by_category": {"food": "4110", "clothing": "4120"}},
        "amount",
        "مبيعات حسب الفئة",
    ),

    # 2 — order.placed.deferred
    (
        "order.placed.deferred", 1, "debit", "1132", None, "deferred_price",
        "ذمم العملاء — آجل",
    ),
    (
        "order.placed.deferred", 2, "credit", None,
        {"by_category": {"food": "4110", "clothing": "4120"}},
        "cash_price",
        "مبيعات حسب الفئة بسعر النقد",
    ),
    (
        "order.placed.deferred", 3, "credit", "4200", None, "spread",
        "فروق التسعير الآجل",
    ),

    # 3 — inventory.issued (location-aware per reviewer round 2)
    (
        "inventory.issued", 1, "debit", None,
        {"by_category": {"food": "5110", "clothing": "5120"}},
        "cost",
        "تكلفة المبيعات حسب الفئة",
    ),
    (
        "inventory.issued", 2, "credit", None,
        {
            "by_location": {
                "supplier": "1151_or_1152",
                "channel_partner": "1153",
                "in_transit": "1154",
            }
        },
        "cost",
        "خصم المخزون من موقع البضاعة",
    ),

    # 5 — payment.ocr.matched (two legs — upload + confirm are posted
    # separately by the receipts service; event '5' = upload leg)
    (
        "payment.ocr.matched.upload", 1, "debit", "1120", None, "amount",
        "التحصيل المعلّق OCR",
    ),
    (
        "payment.ocr.matched.upload", 2, "credit", None,
        {"by_category": {"cash": "1131", "deferred": "1132"}},
        "amount",
        "تسوية ذمة العميل حسب نوع الذمة",
    ),
    (
        "payment.ocr.matched.confirm", 1, "debit", "1112", None, "amount",
        "البنك الجاري",
    ),
    (
        "payment.ocr.matched.confirm", 2, "credit", "1120", None, "amount",
        "إقفال التحصيل المعلّق OCR",
    ),

    # 7 — payment.early_discount.applied
    (
        "payment.early_discount.applied", 1, "debit", "4300", None, "discount",
        "إيراد خصم استحقاق محتسب",
    ),
    (
        "payment.early_discount.applied", 2, "credit", "1132", None, "discount",
        "إسقاط من ذمة العميل الآجلة",
    ),

    # 8 — supply.received
    (
        "supply.received", 1, "debit", None,
        {"by_category": {"food": "1151", "clothing": "1152"}},
        "cost",
        "إضافة المخزون بالتكلفة",
    ),
    (
        "supply.received", 2, "credit", None,
        {"by_category": {"food": "2111", "clothing": "2112"}},
        "cost",
        "دائنون موردون",
    ),

    # 9 — supplier.payment.recorded
    (
        "supplier.payment.recorded", 1, "debit", None,
        {"by_category": {"food": "2111", "clothing": "2112"}},
        "amount",
        "خصم من دائني الموردين",
    ),
    (
        "supplier.payment.recorded", 2, "credit", "1112", None, "amount",
        "البنك الجاري",
    ),

    # 11 — agent.deposit.received
    (
        "agent.deposit.received", 1, "debit", "1111", None, "amount",
        "الصندوق",
    ),
    (
        "agent.deposit.received", 2, "credit", "2120", None, "amount",
        "تأمين الوكيل",
    ),

    # 12 — agent.commission.accrued (reviewer round 2 — 5281 instead of 5280)
    (
        "agent.commission.accrued", 1, "debit", "5281", None, "amount",
        "عمولة الوكلاء — مصروف",
    ),
    (
        "agent.commission.accrued", 2, "credit", "2130", None, "amount",
        "عمولات مستحقة للوكلاء",
    ),

    # 12b — agent.investment_return.accrued (5290 — reviewer round 2)
    (
        "agent.investment_return.accrued", 1, "debit", "5290", None, "amount",
        "عائد استثماري الوكلاء — مصروف",
    ),
    (
        "agent.investment_return.accrued", 2, "credit", "2140", None, "amount",
        "عوائد استثمارية مستحقة للوكلاء",
    ),

    # 13 — production.mo.closed (one line per output, one per material;
    # the engine iterates — v1 posts the simple finished-good leg)
    (
        "production.mo.closed", 1, "debit", None,
        {"by_category": {"food": "1151", "clothing": "1152"}},
        "cost",
        "إضافة المنتج النهائي للمخزون",
    ),
    (
        "production.mo.closed", 2, "credit", None,
        {"by_category": {"food": "1151", "clothing": "1152"}},
        "cost",
        "خصم الخامة من المخزون",
    ),
)


def seed_accounts() -> None:
    code_to_id: dict[str, int] = {}
    for code, name_ar, name_en, type_, parent_code, is_postable, category in COA:
        existing = db.session.execute(
            select(Account).where(Account.code == code)
        ).scalar_one_or_none()
        if existing is not None:
            code_to_id[code] = existing.id
            continue

        parent_id = None if parent_code is None else code_to_id.get(parent_code)
        account = Account(
            code=code,
            name_ar=name_ar,
            name_en=name_en,
            type=type_,
            parent_id=parent_id,
            is_postable=is_postable,
            category=category,
        )
        db.session.add(account)
        db.session.flush()
        code_to_id[code] = account.id
    db.session.commit()


def seed_event_map() -> None:
    for event_type, step, side, account_code, rule_json, amount_source, description in EVENT_MAP:
        existing = db.session.execute(
            select(EventJournalMap).where(
                EventJournalMap.event_type == event_type,
                EventJournalMap.step == step,
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        db.session.add(
            EventJournalMap(
                event_type=event_type,
                step=step,
                side=side,
                account_code=account_code,
                rule_json=rule_json,
                amount_source=amount_source,
                description=description,
            )
        )
    db.session.commit()


def run() -> None:
    seed_accounts()
    seed_event_map()
    n_accounts = db.session.execute(select(Account)).scalars().all()
    n_map = db.session.execute(select(EventJournalMap)).scalars().all()
    print(f"Accounting seed OK — {len(n_accounts)} accounts, {len(n_map)} map rows.")

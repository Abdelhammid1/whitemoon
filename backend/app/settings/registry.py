"""The declared catalogue of tunable business constants (T-37).

Each entry is the single source of truth for a value's default and metadata.
The DB (`SystemSetting`) only stores an admin's override; absent a row, the
default here applies. `source` records where the value used to be hardcoded so
the «الثوابت المنقولة» report can point at it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SettingDef:
    key: str
    group: str  # Arabic group heading on the settings screen
    label: str  # Arabic label
    description: str  # what the value controls
    example: str  # a concrete illustration of its effect
    value_type: str  # "int" | "decimal"
    default: str  # default as a string (cast via value_type)
    unit: str  # Arabic unit suffix, e.g. يوم / دقيقة / %
    minimum: str | None = None
    maximum: str | None = None
    source: str = ""  # file:symbol it was moved from (for the report)


# Order here is the display order; `group` clusters them on the screen.
REGISTRY: tuple[SettingDef, ...] = (
    # ---- الطلبات والسداد المبكر ----
    SettingDef(
        key="orders.early_window_days",
        group="الطلبات والسداد المبكر",
        label="نافذة السداد المبكر",
        description="عدد الأيام التي يسري خلالها خصم السداد المبكر على الطلب الآجل من تاريخ الطلب.",
        example="بقيمة 14: من يسدّد خلال 14 يومًا من الطلب يحصل على خصم السداد المبكر.",
        value_type="int", default="14", unit="يوم", minimum="1", maximum="180",
        source="sales/services/orders.py:EARLY_WINDOW_DAYS",
    ),
    SettingDef(
        key="orders.early_discount_fraction",
        group="الطلبات والسداد المبكر",
        label="نسبة خصم السداد المبكر",
        description="نسبة (من 0 إلى 1) من الفارق بين الإجمالي الآجل والنقدي تُمنح كخصم للسداد المبكر.",
        example="بقيمة 0.50: إذا كان فارق الأجل 100 ج.م، يكون خصم السداد المبكر 50 ج.م.",
        value_type="decimal", default="0.50", unit="نسبة (0–1)", minimum="0", maximum="1",
        source="sales/services/orders.py:EARLY_DISCOUNT_PCT",
    ),
    # ---- السلة ----
    SettingDef(
        key="cart.price_lock_minutes",
        group="السلة والأسعار",
        label="مدة تثبيت سعر النقد",
        description="المدة التي يبقى فيها سعر النقد مثبّتًا للصنف بعد إضافته للسلة قبل العودة للسعر اللحظي.",
        example="بقيمة 60: يبقى السعر مثبّتًا 60 دقيقة من لحظة الإضافة.",
        value_type="int", default="60", unit="دقيقة", minimum="1", maximum="1440",
        source="commerce/services/pricelock.py:HOLD_MINUTES",
    ),
    # ---- التصنيف الائتماني ----
    SettingDef(
        key="credit.rating_window_days",
        group="التصنيف الائتماني",
        label="نافذة احتساب التصنيف",
        description="عدد الأيام الماضية التي يُحسب عليها سجل السداد عند تقييم تصنيف العميل.",
        example="بقيمة 365: يُقيَّم العميل على سلوك سداده خلال آخر سنة.",
        value_type="int", default="365", unit="يوم", minimum="30", maximum="1825",
        source="sales/services/credit.py:WINDOW_DAYS",
    ),
    SettingDef(
        key="credit.min_history",
        group="التصنيف الائتماني",
        label="الحد الأدنى لعدد العمليات",
        description="أقل عدد عمليات سداد مُسوّاة قبل منح العميل تصنيفًا كاملًا (وإلا يُعامَل كحساب جديد).",
        example="بقيمة 3: من لديه أقل من 3 عمليات مُسوّاة يبقى بتصنيف الحساب الجديد.",
        value_type="int", default="3", unit="عملية", minimum="0", maximum="50",
        source="sales/services/credit.py:MIN_HISTORY",
    ),
    SettingDef(
        key="credit.new_account_days",
        group="التصنيف الائتماني",
        label="عمر الحساب الجديد",
        description="عمر الحساب (بالأيام) الذي يُعامَل تحته العميل كحساب جديد بتصنيف متحفّظ.",
        example="بقيمة 90: الحساب الأحدث من 90 يومًا يُعامَل كحساب جديد.",
        value_type="int", default="90", unit="يوم", minimum="0", maximum="365",
        source="sales/services/credit.py:NEW_ACCOUNT_DAYS",
    ),
    SettingDef(
        key="credit.green_score",
        group="التصنيف الائتماني",
        label="عتبة التصنيف الأخضر",
        description="أقل نتيجة سداد (من 100) تمنح العميل التصنيف الأخضر.",
        example="بقيمة 85: من نتيجته 85 فأعلى يحصل على الأخضر.",
        value_type="int", default="85", unit="نقطة", minimum="0", maximum="100",
        source="sales/services/credit.py:GREEN_SCORE",
    ),
    SettingDef(
        key="credit.yellow_score",
        group="التصنيف الائتماني",
        label="عتبة التصنيف الأصفر",
        description="أقل نتيجة سداد (من 100) تُبقي العميل في التصنيف الأصفر بدل الأحمر.",
        example="بقيمة 50: من نتيجته بين 50 و85 يكون أصفر، وأقل من 50 أحمر.",
        value_type="int", default="50", unit="نقطة", minimum="0", maximum="100",
        source="sales/services/credit.py:YELLOW_SCORE",
    ),
    # ---- التصعيد والتحصيل ----
    SettingDef(
        key="credit.payment_reminder_days_before",
        group="التصعيد والتحصيل",
        label="مدة تنبيه السداد قبل الاستحقاق",
        description="قبل كم يوم من تاريخ الاستحقاق يُرسل تذكير السداد للعميل.",
        example="بقيمة 3: يصل التذكير قبل 3 أيام من موعد الاستحقاق.",
        value_type="int", default="3", unit="يوم", minimum="0", maximum="30",
        source="sales/services/credit.py:REMINDER_DAYS_BEFORE",
    ),
    SettingDef(
        key="credit.deescalate_after_hours",
        group="التصعيد والتحصيل",
        label="مهلة خفض مستوى التصعيد",
        description="عدد الساعات بعد تسوية المتأخرات قبل خفض مستوى تصعيد العميل تلقائيًا.",
        example="بقيمة 24: بعد السداد بـ 24 ساعة يُخفَّض مستوى التصعيد.",
        value_type="int", default="24", unit="ساعة", minimum="0", maximum="168",
        source="sales/services/credit.py:DEESCALATE_AFTER_HOURS",
    ),
    SettingDef(
        key="credit.escalation_l2_min_days",
        group="التصعيد والتحصيل",
        label="أيام التأخر لمستوى التصعيد 2",
        description="عدد أيام تأخر الذمة الواحدة الذي يرفع العميل لمستوى التصعيد الثاني.",
        example="بقيمة 8: ذمة متأخرة 8 أيام فأكثر ترفع العميل للمستوى 2.",
        value_type="int", default="8", unit="يوم", minimum="1", maximum="120",
        source="sales/services/credit.py:ESC_L2_MIN_DAYS",
    ),
    SettingDef(
        key="credit.escalation_l4_min_days",
        group="التصعيد والتحصيل",
        label="أيام التأخر لمستوى التصعيد 4",
        description="عدد أيام التأخر الذي يرفع العميل للمستوى 4 (إيقاف كل الطلبات الجديدة حتى السداد).",
        example="بقيمة 31: ذمة متأخرة 31 يومًا فأكثر توقف طلبات العميل الجديدة.",
        value_type="int", default="31", unit="يوم", minimum="1", maximum="365",
        source="sales/services/credit.py:ESC_L4_MIN_DAYS",
    ),
    SettingDef(
        key="credit.escalation_two_dues_min_days",
        group="التصعيد والتحصيل",
        label="أيام التأخر لذمتين (مستوى 2)",
        description="إذا تأخرت ذمتان مفتوحتان هذا العدد من الأيام أو أكثر، يُرفع العميل للمستوى 2.",
        example="بقيمة 7: ذمتان متأخرتان 7 أيام فأكثر ترفعان العميل للمستوى 2.",
        value_type="int", default="7", unit="يوم", minimum="1", maximum="120",
        source="sales/services/credit.py:ESC_TWO_DUES_MIN_DAYS",
    ),
    SettingDef(
        key="credit.escalation_l2_limit_cut_fraction",
        group="التصعيد والتحصيل",
        label="نسبة خفض السقف عند المستوى 2",
        description="نسبة (من 0 إلى 1) يُخفَّض بها السقف الائتماني الفعّال للعميل عند بلوغ التصعيد المستوى 2.",
        example="بقيمة 0.50: يُخفَّض السقف الفعّال إلى النصف عند المستوى 2.",
        value_type="decimal", default="0.50", unit="نسبة (0–1)", minimum="0", maximum="1",
        source="sales/services/credit.py:ESC_LIMIT_CUT",
    ),
    # ---- المخزون ----
    SettingDef(
        key="inventory.reorder_escalate_after_hours",
        group="المخزون",
        label="مهلة تصعيد تنبيه إعادة الطلب",
        description="عدد الساعات التي يبقى عندها تنبيه إعادة الطلب دون معالجة قبل تصعيده للمستوى التالي.",
        example="بقيمة 24: تنبيه إعادة طلب لم يُعالَج خلال 24 ساعة يُصعَّد.",
        value_type="int", default="24", unit="ساعة", minimum="1", maximum="168",
        source="inventory/services/reorder.py:ESCALATE_AFTER_HOURS",
    ),
    # ---- المورد والعميل ----
    SettingDef(
        key="supplier.discount_expiry_soon_days",
        group="المورد والعميل",
        label="تنبيه قرب انتهاء الخصم",
        description="قبل كم يوم من انتهاء خصم المورد يظهر في بطاقة «خصومات ستنتهي قريبًا».",
        example="بقيمة 7: يظهر الخصم الذي سينتهي خلال 7 أيام في لوحة المورد.",
        value_type="int", default="7", unit="يوم", minimum="1", maximum="90",
        source="commerce/services/supplier_home.py:DISCOUNT_EXPIRY_SOON_DAYS",
    ),
    SettingDef(
        key="customer.usual_window_days",
        group="المورد والعميل",
        label="نافذة «أصنافي/فئاتي المعتادة»",
        description="عدد الأيام الماضية التي تُستنتَج منها عادات شراء العميل لاقتراح أصنافه وفئاته المعتادة.",
        example="بقيمة 90: تُبنى العادات على مشتريات آخر 90 يومًا.",
        value_type="int", default="90", unit="يوم", minimum="7", maximum="365",
        source="commerce/services/customer_shop.py:USUAL_CATEGORY_WINDOW_DAYS",
    ),
)

BY_KEY: dict[str, SettingDef] = {d.key: d for d in REGISTRY}


def cast(defn: SettingDef, raw: str) -> int | Decimal:
    return int(raw) if defn.value_type == "int" else Decimal(raw)

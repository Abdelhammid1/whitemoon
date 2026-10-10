# T-37 — تقرير الثوابت التجارية المنقولة إلى «إعدادات النظام»

كل القيم التالية كانت ثوابت مكتوبة في الكود، ونُقلت إلى سجل إعدادات موحّد تُقرأ منه وقت الاستخدام (مفتاح واحد لكل قيمة)، وأصبحت قابلة للتعديل من شاشة «إعدادات النظام» بصلاحية `system.settings.manage` مع تسجيل كل تغيير.

**الإجمالي:** 17 قيمة في 6 مجموعات.

## الطلبات والسداد المبكر

| المفتاح | الوصف | الافتراضي | الوحدة | الحدود | المصدر السابق |
|---|---|---|---|---|---|
| `orders.early_window_days` | نافذة السداد المبكر | 14 | يوم | 1–180 | `sales/services/orders.py:EARLY_WINDOW_DAYS` |
| `orders.early_discount_fraction` | نسبة خصم السداد المبكر | 0.50 | نسبة (0–1) | 0–1 | `sales/services/orders.py:EARLY_DISCOUNT_PCT` |

## السلة والأسعار

| المفتاح | الوصف | الافتراضي | الوحدة | الحدود | المصدر السابق |
|---|---|---|---|---|---|
| `cart.price_lock_minutes` | مدة تثبيت سعر النقد | 60 | دقيقة | 1–1440 | `commerce/services/pricelock.py:HOLD_MINUTES` |

## التصنيف الائتماني

| المفتاح | الوصف | الافتراضي | الوحدة | الحدود | المصدر السابق |
|---|---|---|---|---|---|
| `credit.rating_window_days` | نافذة احتساب التصنيف | 365 | يوم | 30–1825 | `sales/services/credit.py:WINDOW_DAYS` |
| `credit.min_history` | الحد الأدنى لعدد العمليات | 3 | عملية | 0–50 | `sales/services/credit.py:MIN_HISTORY` |
| `credit.new_account_days` | عمر الحساب الجديد | 90 | يوم | 0–365 | `sales/services/credit.py:NEW_ACCOUNT_DAYS` |
| `credit.green_score` | عتبة التصنيف الأخضر | 85 | نقطة | 0–100 | `sales/services/credit.py:GREEN_SCORE` |
| `credit.yellow_score` | عتبة التصنيف الأصفر | 50 | نقطة | 0–100 | `sales/services/credit.py:YELLOW_SCORE` |

## التصعيد والتحصيل

| المفتاح | الوصف | الافتراضي | الوحدة | الحدود | المصدر السابق |
|---|---|---|---|---|---|
| `credit.payment_reminder_days_before` | مدة تنبيه السداد قبل الاستحقاق | 3 | يوم | 0–30 | `sales/services/credit.py:REMINDER_DAYS_BEFORE` |
| `credit.deescalate_after_hours` | مهلة خفض مستوى التصعيد | 24 | ساعة | 0–168 | `sales/services/credit.py:DEESCALATE_AFTER_HOURS` |
| `credit.escalation_l2_min_days` | أيام التأخر لمستوى التصعيد 2 | 8 | يوم | 1–120 | `sales/services/credit.py:ESC_L2_MIN_DAYS` |
| `credit.escalation_l4_min_days` | أيام التأخر لمستوى التصعيد 4 | 31 | يوم | 1–365 | `sales/services/credit.py:ESC_L4_MIN_DAYS` |
| `credit.escalation_two_dues_min_days` | أيام التأخر لذمتين (مستوى 2) | 7 | يوم | 1–120 | `sales/services/credit.py:ESC_TWO_DUES_MIN_DAYS` |
| `credit.escalation_l2_limit_cut_fraction` | نسبة خفض السقف عند المستوى 2 | 0.50 | نسبة (0–1) | 0–1 | `sales/services/credit.py:ESC_LIMIT_CUT` |

## المخزون

| المفتاح | الوصف | الافتراضي | الوحدة | الحدود | المصدر السابق |
|---|---|---|---|---|---|
| `inventory.reorder_escalate_after_hours` | مهلة تصعيد تنبيه إعادة الطلب | 24 | ساعة | 1–168 | `inventory/services/reorder.py:ESCALATE_AFTER_HOURS` |

## المورد والعميل

| المفتاح | الوصف | الافتراضي | الوحدة | الحدود | المصدر السابق |
|---|---|---|---|---|---|
| `supplier.discount_expiry_soon_days` | تنبيه قرب انتهاء الخصم | 7 | يوم | 1–90 | `commerce/services/supplier_home.py:DISCOUNT_EXPIRY_SOON_DAYS` |
| `customer.usual_window_days` | نافذة «أصنافي/فئاتي المعتادة» | 90 | يوم | 7–365 | `commerce/services/customer_shop.py:USUAL_CATEGORY_WINDOW_DAYS` |

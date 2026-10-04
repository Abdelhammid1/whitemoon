# 20 — Stitch prompt: re-skin the as-built screens

Paste the **SYSTEM PREAMBLE** once into a Stitch project (or set it as the
project style), then generate each screen from its block. Each block matches a
screen that already exists and is wired to the backend — so the generated
design maps 1:1 and gets implemented as a pure re-skin (no behaviour change).

Generate **desktop + mobile** for the customer/rep screens (catalog, cart,
order detail, RFQ, POS terminal, tracking, chat thread, notifications).

---

## SYSTEM PREAMBLE (paste first)

> Design a screen for **White Moon (وايت مون)**, an Arabic-first **B2B**
> marketplace + ERP for Egypt. Reuse this exact design system — don't invent
> colors, fonts, or spacing.
>
> **Direction/language:** full **RTL**, all copy **Arabic**. Numbers, money,
> codes, dates, IDs render **LTR** (isolated inline) in **JetBrains Mono**.
> Currency is **Egyptian Pound only** — show `ج.م`, never another currency.
>
> **Fonts:** `IBM Plex Sans Arabic` for text; `JetBrains Mono` for numbers/codes.
> Icons: **Material Symbols Outlined**.
>
> **Colors (warm grey, near-monochrome, black primary):** background/surface
> `#fbf9f9`; cards `#ffffff`; raised rows `#f5f3f3`; hairlines `#e9e8e7` /
> `#c4c7c7`; text `#1b1c1c`, secondary `#444748`; **primary `#000000`** /
> on-primary `#ffffff`; error `#ba1a1a`. Status only as small dots/pills: green
> `#0F6B3E`, amber `#A8650C`, red `#ba1a1a`, neutral grey. No gradients.
>
> **Type scale:** display 28/36·500, headline-1 20/28·500, headline-2 16/24·500,
> body 14/22·400, small 13/20·400, mono-body 13/20·400. Radii: 0.25 / lg 0.5 /
> xl 0.75rem, pills full. Spacing: xs .25 / sm .5 / md 1 / lg 1.5 / xl 2rem.
>
> **Shell:** fixed right-hand (RTL) sidebar with grouped nav + brand "وايت مون"
> on top; slim top bar with the signed-in user (`person` icon). Content column
> ~1100px, generous whitespace. **Tables are ledger-style:** header on `#f5f3f3`
> with one hairline under it, rows split by one hairline, no zebra, no outer
> border. Buttons: primary = solid black; secondary = text/outline; destructive
> = red text. Pills are small, rounded-full, quiet. Every screen has loading
> (thin spinner), empty (calm centered line), and inline error (one red line).
> Minimal, data-dense, enterprise — not flashy.

**Platform rules (honor where relevant):** a customer never sees a supplier's
identity (catalog/cart/orders/RFQ show product + price only; RFQ offers are
"عرض #N"); money is EGP `ج.م`; deferred-sale terms are shown read-only
(server-computed); mediated chat hides the counterpart and flags blocked
messages.

---

## Marketplace — customer

**Catalog** (`/catalog`) — header "الكتالوج" + "السلة" button; search field +
category chips (الكل/غذائية/ملابس); responsive card grid. Each card: product
name, category pill, **best price** `ج.م` (mono, large), a qty stepper, and a
black "أضف للسلة" button. A quiet note "السعر يُثبَّت ٦٠ دقيقة عند الإضافة".
**No supplier anywhere.**

**Cart** (`/cart`) — ledger table: product, qty, locked unit price (with a
small "مثبّت" tag), line total, delete. Summary line "الإجمالي" large in `ج.م`.
Two actions: "طلب نقدي" (primary) and "طلب آجل". Confirm modal for each; the
deferred modal notes terms are computed server-side and may be rejected over
the credit limit.

**My orders** (`/orders`) — table: order number, payment (نقدي/آجل), total,
status pill (قيد الانتظار/مؤكد/منفَّذ/ملغى), date.

**Order detail** (`/orders/:id`) — status pill + payment + date; lines table
(product, qty, unit price, line total); total; a "تتبع الشحنة" link.

**RFQ — new** (`/rfq`) — form: رقم المنتج, الكمية, آخر موعد (date, optional),
متطلبات التأهيل (optional); submit. Note the company mediates, suppliers hidden.

**RFQ — detail** (`/rfq/:id`) — RFQ summary pills; offers table showing
**"عرض #N"**, سعر الوحدة, أدنى كمية, التاريخ — **no supplier**.

## Credit & customers — finance

**Credit lookup** (`/credit`) — "رقم العميل" field + عرض. Result: **colour tier
pill** (أبيض/أخضر/أصفر/أحمر) + score; a 4-row stat list (السقف الافتراضي,
الفعّال, نسبة الآجل %, المستحق) in `ج.م`; buttons إعادة الاحتساب / استثناء على
السقف / تجميد (مستوى ٥, red); an escalation history table.

**Tier settings** (`/credit/tiers`) — four editable rows (لون, السقف `ج.م`,
الآجل %) each with حفظ; a "تشغيل فحص التصعيد" button in the header.

**Payment approval** (`/credit/payments`) — a collect form (رقم العميل, رقم
الذمة optional, المبلغ) + a table of approval requests (المعرف, العميل, الذمة,
المبلغ, status pill معلّق/معتمد/مرفوض) with رفض/اعتماد actions on pending rows.

## Compliance — finance

**ETA readiness** (`/compliance`) — 4 KPI tiles (إجمالي الأصناف, جاهزة, غير
جاهزة, بدون كود); a "ضبط كود الصنف" form (رقم المنتج, كود الصنف, "جاهز للربط"
checkbox); a banner "كل المعاملات بالجنيه المصري" + "لا ربط فعلي بمصلحة الضرائب".

## Partners (agents & branches) — admin

**Partners** (`/partners`) — "شريك جديد" button; table: المعرف, الاسم, النوع
pill (وكيل/فرع), النطاق. Create modal: type toggle وكيل/فرع, الاسم, النطاق
الجغرافي, البريد, كلمة المرور.

**Partner detail** (`/partners/:id`) — three sections: **الشروط** (toggles
"يستحق عمولة" + %, "عائد استثماري" + %, save); **التأمينات** (record form
amount+conditions, list with status محتجز/مُسترد + رد); **الاستحقاقات**
(kind toggle عمولة/عائد + سنة/شهر + احتساب, list of accruals).

## Production — admin

**Manufacturing orders** (`/production`) — "أمر تصنيع جديد" button; table:
الرقم, المنتج, الكمية, التكلفة, status pill (مسودة/قيد التنفيذ/مكتمل/ملغى).
Create modal: output product + qty, stages (comma text), repeatable material
rows (product id, qty, unit cost).

**MO detail** (`/production/:id`) — status; **stages list** with "إتمام المرحلة
التالية"; materials table + total cost; "إغلاق الأمر" (enabled only when all
stages done) + "إلغاء" (red). Show journal ref once completed.

## POS — agent/branch + admin

**Terminal** (`/pos`) — touch-friendly; repeatable line rows (product id,
supplier id, qty) with "+ صنف"; big "إتمام البيع (نقدي)". After sale: a summary
card (number, posted/unposted pill, total `ج.م`). Price comes from the offer,
not entered.

**My sales** (`/pos/sales`) — table: الرقم, عدد الأصناف, الإجمالي, الترحيل pill.

**Settlement** (`/pos/settle`, admin) — unposted count + total + "ترحيل
التسوية"; list of unposted sales; a "آخر تسوية" summary (batch id, count, total,
journal ref).

## Logistics

**Ops** (`/logistics`, admin) — **إضافة موعد تسليم** form (date, window,
capacity) + available-slots table (date, window, remaining/capacity);
**إدارة شحنة** (order id lookup → status pill, شحن/في الطريق buttons, "+ مسار
خارجي", legs table).

**Tracking** (`/orders/:id/shipment`, customer) — status **timeline** (مجدول →
تم الشحن → في الطريق → تم التسليم, with a failed branch); current GPS location
line; a large **confirmation code** card "سلّم هذا الرمز للمندوب".

**Delivery confirmation** (rep, mobile) — *not yet built as a page* — confirm
via code **or** signature pad + shortage lines (product, qty, photo). Design it
for a future rep screen.

## Chat (mediated)

**Conversations** (`/chat`) — moderator gets a "المحظورة فقط" filter; table:
المحادثة, الموضوع, الطرف الآخر (role only for participants; ids for moderator),
status pill (مفتوحة/مغلقة/محظورة).

**Thread** (`/chat/:id`) — chat bubbles aligned mine/theirs, labeled by role +
time; a blocked message shows a red "حُجبت: محاولة تبادل بيانات اتصال" banner; a
composer (textarea + إرسال). Note "كل الرسائل تمر عبر الشركة".

## Cross-cutting

**Executive dashboard** (`/dashboard`, finance) — KPI tiles: الإيرادات
المتحققة, الذمم المستحقة, المتعثّرة, نقص المخزون, مبيعات POS غير مُرحَّلة,
محادثات مفتوحة/محظورة (mono, `ج.م`); plus status-breakdown rows (الطلبات,
الشحنات, أوامر التصنيع, الذمم) as small pills.

**Notification center** (`/notifications`, all roles) — header with unread count
+ "تعليم الكل كمقروء"; a list of notifications (title, body, channel pill
داخل‑التطبيق/SMS/واتساب/بريد, time, unread dot). Click an unread to mark read.

---

### After you generate
Export the same way as before. I implement each as a **re-skin** of the
existing page (same routes, data, and guards) — nothing about behaviour or the
backend changes.

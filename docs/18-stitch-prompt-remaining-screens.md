# 18 — Stitch prompt: remaining screens (EPICs 1, 5–11)

Paste the **System preamble** once at the top of a Stitch project, then
generate each screen with its block. Every screen must look like it belongs to
the same product as the already-built identity/accounting/inventory screens.

---

## SYSTEM PREAMBLE (paste first, applies to every screen)

> Design a screen for **White Moon (وايت مون)**, an Arabic-first **B2B**
> marketplace + ERP for the Egyptian market. Reuse this exact design system —
> do not invent new colors, fonts, or spacing.
>
> **Direction & language:** Full **RTL**, all UI copy in **Arabic**. Numbers,
> money, codes, dates and IDs render **LTR** inside the RTL layout (use an
> isolated inline span). Currency is **Egyptian Pound only** — show `ج.م`,
> never another currency or symbol.
>
> **Fonts:** `IBM Plex Sans Arabic` for all text; `JetBrains Mono` for money,
> quantities, codes, IDs, dates. Icons: **Material Symbols Outlined**.
>
> **Color tokens (light, warm grey — almost monochrome, black primary):**
> background/surface `#fbf9f9`; cards `surface-container-lowest #ffffff`;
> raised rows `surface-container-low #f5f3f3`; hairlines
> `surface-container-high #e9e8e7` / `outline-variant #c4c7c7`; text
> `on-surface #1b1c1c`, secondary `on-surface-variant #444748`; **primary
> `#000000`** with `on-primary #ffffff`; error `#ba1a1a`. No accent gradients.
> Status colors used **only** as small dots/pills: green `#2e7d32`, amber
> `#b26a00`, red `#ba1a1a`, neutral grey.
>
> **Type scale:** display 28/36 500; headline-1 20/28 500; headline-2 16/24
> 500; body 14/22 400; small 13/20 400; mono-body 13/20 400. Radii: default
> 0.25rem, lg 0.5rem, xl 0.75rem, pills full. Spacing scale: xs .25 / sm .5 /
> md 1 / lg 1.5 / xl 2 rem; page gutter 1rem, content margin 1.5rem.
>
> **App shell:** fixed right-hand sidebar (RTL) with grouped nav links and a
> brand mark "وايت مون" at the top; a slim top bar showing the signed-in
> user with a `person` icon. Content column max ~1100px, generous whitespace.
> Tables are **ledger-style**: header on `surface-container-low` with a single
> hairline under it, rows divided by one hairline, **no zebra striping, no
> outer border**. Buttons: primary = solid black; secondary = text/outline;
> destructive = red text. Pills are small, rounded-full, quiet.
>
> **Every screen includes three states:** loading (thin skeleton/spinner),
> empty (calm centered message, no illustration clutter), and inline error
> (one red line). Keep it minimal, data-dense, enterprise — not flashy.

**Platform-wide non-negotiables (honor on the relevant screens):**
- A customer **never** sees a supplier's identity anywhere — not in catalog,
  cart, orders, or RFQ offers. Show product + price only; anonymize offers as
  "عرض ‎#".
- All money EGP (`ج.م`). Deferred-sale terms are **shown read-only** (computed
  by the server); the customer never types a markup/discount.
- Mediated chat hides the counterpart's identity; blocked messages are shown
  to the sender as blocked, never delivered to the other side.

---

## EPIC 1 — Marketplace (customer-facing)

Nav group **"السوق"**: الكتالوج · سلتي · طلباتي · طلبات عروض الأسعار.

**M1 — Catalog / كتالوج المنتجات** (`/catalog`)
> A searchable product catalog for a B2B customer. Top: search field
> (اسم/كود) and category chips (الكل · غذائية · ملابس). A responsive grid of
> product cards; each card: product name (Arabic), a category pill, the **best
> available price** in `ج.م` (mono), the minimum order qty, and — when
> relevant — a small quiet badge "يوجد سعر أقل" (lower-price hint). A primary
> "أضف للسلة" button with a qty stepper. **No supplier name anywhere.** Empty
> state: "لا توجد منتجات مطابقة".

**M2 — Product detail / تفاصيل المنتج** (`/catalog/:id`)
> Single product: name, category pill, unit, large best-price in `ج.م`, MOQ,
> and the "يوجد سعر أقل" hint if present (no competitor price or identity). A
> qty stepper + "أضف للسلة"; a note that adding to cart **locks the price for
> 60 minutes** on the reserved quantity.

**M3 — Cart / سلتي** (`/cart`)
> Unified cart that may span multiple suppliers but shows **none of them**. A
> ledger table of lines: product, qty (editable stepper), locked unit price
> (mono `ج.م`, with a tiny "سعر مثبّت" tag), line total; a remove icon.
> Right/bottom summary card: subtotal, item count, "إتمام الطلب" primary. A
> small note if any locked price expired and reverted to the live price.
> Empty: "سلتك فارغة".

**M4 — Checkout / إتمام الطلب** (`/checkout`)
> Review + place order. A payment-mode toggle: **نقدي** / **آجل**. When
> **آجل** is selected, reveal a **read-only** terms panel (server-computed):
> deferred total, early-settlement discount and its window (e.g. "خصم للسداد
> خلال ١٤ يومًا"), and the due date — clearly labeled "محتسبة تلقائيًا".
> Show the customer's credit status line. Primary "تأكيد الطلب". Include the
> blocked states as calm inline errors: "تجاوز السقف الائتماني" and "التصنيف
> الأحمر لا يسمح بالبيع الآجل — نقدي فقط".

**M5 — My orders / طلباتي** (`/orders`)
> Ledger table: order number (mono), status pill (قيد الانتظار / مؤكد / ملغى /
> منفَّذ), total `ج.م`, date. Row click → order detail.

**M6 — Order detail (customer) / تفاصيل الطلب** (`/orders/:id`)
> Header: number, status pill, placed date, totals (cash + deferred if any).
> A lines table (product, qty, unit price, line total) — **merged, no supplier
> breakdown**. If a deferred order: the Shariah terms panel (read-only). A
> "تتبع الشحنة" link to logistics tracking.

**M7 — New RFQ / طلب عرض سعر** (`/rfq/new`)
> Simple form: product, quantity, optional note/spec, submit. Explain the
> company mediates and supplier identities stay hidden.

**M8 — RFQ detail / عروض الأسعار** (`/rfq/:id`)
> The RFQ summary at top; below, a list of received offers shown as **"عرض
> ‎#1، ‎#2…"** with price (`ج.م`) and validity **only — never the supplier**.
> Each offer has an "اعتماد العرض" action. Empty: "لم تصل عروض بعد".

---

## EPIC 5 — Credit & customers (finance / admin)

Nav group **"المبيعات والعملاء"**: التصنيف الائتماني · الذمم · التصعيد.

**C1 — Credit overview / التصنيف الائتماني** (`/credit`)
> A customers table with a **color tier** as the lead signal — a filled dot +
> pill in one of exactly four colors: **أبيض/white, أخضر/green, أصفر/yellow,
> أحمر/red** (no orange). Columns: customer, tier pill, score (mono), effective
> limit `ج.م`, outstanding `ج.م`. Filter chips by tier. Row → detail.

**C2 — Customer credit detail / ملف العميل الائتماني** (`/credit/:id`)
> Header: customer + big tier pill + score. A stats row: default limit,
> **effective limit**, deferred % allowed, current outstanding (all `ج.م`
> mono). Actions: "إعادة الاحتساب", and "استثناء على السقف" (opens a modal
> requiring a **reason ≥ 5 chars** + new limit). A dues sub-table (see C3). An
> escalations timeline (levels 1–5 with dates, auto vs manual). A dangerous
> "تجميد الحساب (المستوى ٥)" button gated to senior admin, modal with
> mandatory reason.

**C3 — Dues ledger / الذمم** (`/credit/dues` and embedded in C2)
> Ledger table: customer, amount `ج.م`, due date, status pill (مفتوحة/
> مسدّدة/متعثّرة), days late (mono). A "تسجيل سداد" action per open due →
> modal with payment date (must be ≤ today). Note that >90 days late marks
> "متعثّرة".

**C4 — Dunning board / لوحة التصعيد** (`/credit/escalation`)
> Overview of customers in escalation, grouped by level 1→5 with the trigger
> reason and date, auto/manual tag. A "تشغيل فحص التصعيد" button (runs the
> overdue scan). Level 5 shown as a red "مُجمّد" state.

---

## EPIC 6 — Agents & branches (admin + partner self-view)

Nav group **"الوكلاء والفروع"**.

**P1 — Partners list / الوكلاء والفروع** (`/partners`)
> Table of channel partners: display name, **type pill (وكيل / فرع)**, geo
> scope, deposit held `ج.م`, this month's accrual `ج.م`. Filter by type.

**P2 — Partner detail / ملف الشريك** (`/partners/:id`)
> Header: name + type pill + geo scope. Tabs or sections:
> 1. **الشروط** — toggles "يستحق عمولة" (+ % field) and "يستحق عائدًا
>    استثماريًا" (+ % field). **For a branch, hide both earning sections
>    entirely** (branches earn neither).
> 2. **التأمينات** — list of deposits (amount `ج.م`, date, recovery
>    conditions, status محتجز/مُسترد); "تسجيل تأمين" (amount, date, recovery
>    conditions) and "رد التأمين" (reason) actions.
> 3. **الاستحقاقات** — monthly accruals table (kind عمولة/عائد، period،
>    basis `ج.م`، rate %، amount `ج.م`); "احتساب لشهر" picker; a "كشف
>    تفصيلي" that lists the realized orders behind a period's basis.

---

## EPIC 7 — Production

Nav group **"الإنتاج"**.

**PR1 — Manufacturing orders / أوامر التصنيع** (`/production`)
> Table: MO number (mono), output product, output qty, status pill (مسودة /
> قيد التنفيذ / مكتمل / ملغى), location. "أمر تصنيع جديد" primary.

**PR2 — MO detail / تفاصيل أمر التصنيع** (`/production/:id`)
> Header: number + status. A **stages stepper** (ordered, each مرحلة shown
> pending/done with a "إتمام المرحلة" on the next pending one). A materials
> (BOM) table: material product, qty, unit cost, line cost. Total material
> cost `ج.م`. "إغلاق الأمر" primary — enabled **only when all stages are
> done** — with a note that it auto-deducts materials, adds the finished good,
> and posts the linked journal. "إلغاء" destructive. Show the journal entry
> reference once completed.

**PR3 — New MO / أمر تصنيع جديد** (`/production/new`)
> Form: output product + output qty; a repeatable materials list (product,
> qty, unit cost); an ordered list of stage names (add/reorder/remove). Submit
> → draft.

---

## EPIC 8 — POS (branch / agent)

Nav group **"نقطة البيع"**.

**POS1 — Terminal / نقطة البيع** (`/pos`)
> A fast, touch-friendly sell screen (larger tap targets than the ERP tables).
> Left: product search + quick-add; center: the current sale's lines (product,
> qty stepper, unit price **auto-filled from the active offer — not editable**,
> line total); a big running total in `ج.م`. Primary "إتمام البيع (نقدي)".
> Note: sells from the cashier's own location; stock is deducted immediately.

**POS2 — My sales / مبيعاتي** (`/pos/sales`)
> The cashier's own completed sales: number, total `ج.م`, posted/unposted
> pill. (A cashier sees only their own.)

**POS3 — Settlement / تسوية نقطة البيع** (`/pos/settle`, admin)
> Unposted sales summarized **by category** with totals `ج.م`; a single
> "ترحيل التسوية" button that batch-posts the accounting entries (end-of-day),
> then shows the created journal entry references. Note POS accounting is
> batched, not real-time.

---

## EPIC 9 — Logistics

Nav group **"اللوجستيات"**.

**L1 — Slot picker / اختيار موعد التسليم** (customer, within checkout/order)
> A date selector with available delivery windows as selectable chips/cards;
> **full windows are disabled/greyed with "مكتمل"**. Selecting one books it and
> reveals a **confirmation code** to hand the delivery rep.

**L2 — Shipment tracking / تتبع الشحنة** (`/orders/:id/shipment`, customer)
> A status timeline: مجدول → تم الشحن → في الطريق → تم التسليم (with failed
> branch). A **live map** area showing the rep's current location when
> in-transit. The customer's **confirmation code** displayed prominently.
> Carrier shown generically (أسطول داخلي / شركة شحن) without personal details.

**L3 — Dispatch board / إدارة الشحنات** (`/logistics`, ops)
> Shipments table: order, slot/window, carrier type, status pill, current
> location timestamp. Actions to advance status (شحن / في الطريق / فشل) and
> assign carrier. Capacity view of slots per day.

**L4 — Delivery confirmation / تأكيد التسليم** (`/logistics/deliver/:id`, rep — mobile layout)
> Mobile-first. Confirm receipt via **either** the customer's confirmation
> code **or** an on-screen **signature** pad. A "نواقص؟" section to add
> shortage lines (product, qty, **photo upload**) that attach to the returns
> log. Primary "تأكيد التسليم". Wrong code → inline error.

---

## EPIC 10 — Communication (mediated chat)

Nav group **"المحادثات"**.

**CH1 — Conversations / المحادثات** (`/chat`)
> A list of conversation threads showing the **counterpart by role only**
> ("المورد" / "العميل") — never a name or id — with order context, last
> message snippet, unread/flagged indicator. Open → thread.

**CH2 — Thread / محادثة** (`/chat/:id`)
> A chat thread: messages aligned by mine/theirs, labeled by role, timestamps
> (mono). A composer with a text field and an image attach button. When a
> message is **blocked** (phone number / contact attempt detected, incl. in an
> image), show it to the sender with a red "حُجبت: محاولة تبادل بيانات
> اتصال" banner and it is **not delivered**. Make the mediation explicit:
> "كل الرسائل تمر عبر الشركة".

**CH3 — Moderation console / مراقبة المحادثات** (`/chat/admin`, admin)
> All conversations with search + a "المحظورة فقط" filter; the admin view
> **does** show both parties' ids. Each row → full thread including blocked
> messages, for oversight.

---

## EPIC 11 — Compliance

Nav group **"الامتثال"**.

**CO1 — ETA readiness / جاهزية الفاتورة الإلكترونية** (`/compliance`)
> A dashboard: counts of products ETA-ready vs not, and a list of products
> missing an ETA item code. A products table: product, ETA item code (mono,
> editable), **"جاهز للربط" toggle** (cannot be enabled without a code). A
> banner: "كل المعاملات بالجنيه المصري" and "لا ربط فعلي بمصلحة الضرائب في
> هذا الإصدار". Set-ETA action per row.

---

## Cross-cutting (optional — only if we build their backends next)

**BI — لوحة التحليلات التنفيذية** (`/dashboard`, senior admin)
> One executive screen with KPI tiles: realized revenue, outstanding +
> defaulted dues, low-stock slots, unsettled POS total, shipments by status,
> production orders by status, flagged conversations. Quiet tiles, mono
> numbers, `ج.م`. (Pairs with a BI aggregation endpoint — not built yet.)

**NC — مركز الإشعارات** (`/notifications`)
> A notifications list (type, message, time, read/unread), mark-as-read, and
> a channel legend (داخل التطبيق · SMS · واتساب · بريد). (Pairs with a
> Notification Center backend — not built yet.)

---

### Generation tips for Stitch
- Generate **one screen per prompt**, pasting the System preamble context each
  time (or set it as the project style).
- Ask for **desktop + mobile** variants of M1–M8, L2, L4, POS1, CH2.
- When a screen shows money or IDs, remind Stitch: "render numbers LTR in
  JetBrains Mono, currency `ج.م`".
- Export the same way as before; I'll implement (not redesign) and wire each
  screen to its endpoint, deleting only anything out of plan.

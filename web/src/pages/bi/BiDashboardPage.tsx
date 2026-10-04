import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { Spinner, InlineError, Dot } from '../../components/ui'
import { getDashboard, type Dashboard } from '../../api/bi'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

/* status key → Arabic label + signal tone (ledger dots only, per DESIGN.md) */
type Tone = 'signal' | 'warning' | 'error' | 'neutral'

const STATUS_AR: Record<string, string> = {
  draft: 'مسودة',
  pending: 'قيد الانتظار',
  confirmed: 'مؤكد ومقبول',
  fulfilled: 'تم التجهيز والتنفيذ',
  cancelled: 'ملغى أو مرفوض',
  rejected: 'مرفوض',
  scheduled: 'مجدولة للشحن',
  shipped: 'خرجت من المستودع',
  in_transit: 'في الطريق',
  delivered: 'تم التسليم والتحصيل',
  failed: 'فشل التسليم',
  in_progress: 'قيد التشغيل والإنتاج',
  completed: 'مكتمل وجاهز للمخزن',
  open: 'مفتوحة / قائمة',
  partial: 'سداد جزئي',
  paid: 'مسدّدة',
  overdue: 'متأخرة',
  defaulted: 'متعثّرة',
  due: 'مستحقة',
}

const STATUS_TONE: Record<string, Tone> = {
  confirmed: 'signal',
  fulfilled: 'signal',
  delivered: 'signal',
  completed: 'signal',
  paid: 'signal',
  pending: 'warning',
  in_transit: 'warning',
  shipped: 'warning',
  in_progress: 'warning',
  scheduled: 'warning',
  partial: 'warning',
  overdue: 'warning',
  due: 'warning',
  cancelled: 'error',
  rejected: 'error',
  failed: 'error',
  defaulted: 'error',
  draft: 'neutral',
  open: 'neutral',
}

function MonoNum({ value, tone = 'default' }: { value: React.ReactNode; tone?: 'default' | 'error' }) {
  return (
    <span
      className={`font-mono-medium text-display tracking-tight ${tone === 'error' ? 'text-error' : 'text-on-surface'}`}
      dir="ltr"
    >
      {value}
    </span>
  )
}

/** One executive KPI tile: label + badge, large mono value, a quiet hint line. */
function Tile({
  label,
  value,
  unit,
  hint,
  tone = 'neutral',
  badge,
}: {
  label: string
  value: React.ReactNode
  unit?: string
  hint: string
  tone?: Tone
  badge?: React.ReactNode
}) {
  return (
    <div className="p-space-lg bg-surface-container-lowest border border-surface-container-high flex flex-col justify-between h-[160px]">
      <div className="flex items-center justify-between gap-space-sm">
        <span className="font-small text-small text-secondary">{label}</span>
        {badge}
      </div>
      <div className="flex items-baseline gap-space-xs">
        <MonoNum value={value} tone={tone === 'error' ? 'error' : 'default'} />
        {unit && (
          <span className={`font-small text-small ${tone === 'error' ? 'text-error' : 'text-secondary'}`}>
            {unit}
          </span>
        )}
      </div>
      <div
        className={`flex items-center gap-space-xs font-small text-small ${
          tone === 'error' ? 'text-error' : tone === 'warning' ? 'text-[#A8650C]' : 'text-secondary'
        }`}
      >
        <Dot tone={tone} />
        <span>{hint}</span>
      </div>
    </div>
  )
}

/** One breakdown card: title + total, then a hairline list of statuses. */
function Breakdown({ title, map }: { title: string; map: Record<string, number> }) {
  const entries = Object.entries(map)
  const total = entries.reduce((s, [, v]) => s + v, 0)
  return (
    <div className="p-space-md bg-surface-container-lowest border border-surface-container-high flex flex-col justify-between">
      <div className="flex items-center justify-between pb-space-sm mb-space-sm border-b border-surface-container-highest">
        <span className="font-headline-2 text-headline-2 text-on-surface">{title}</span>
        <span className="font-mono-medium text-mono-medium text-secondary" dir="ltr">
          {total}
        </span>
      </div>
      <div className="flex flex-col gap-space-sm">
        {entries.length === 0 ? (
          <span className="font-small text-small text-secondary">—</span>
        ) : (
          entries.map(([k, v]) => {
            const tone = STATUS_TONE[k] ?? 'neutral'
            return (
              <div key={k} className="flex items-center justify-between font-small text-small">
                <span className="flex items-center gap-space-xs text-secondary">
                  <Dot tone={tone} />
                  {STATUS_AR[k] ?? k}
                </span>
                <span
                  className={`font-mono-body ${tone === 'error' ? 'text-error' : 'text-on-surface'}`}
                  dir="ltr"
                >
                  {v}
                </span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

export function BiDashboardPage() {
  const [d, setD] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getDashboard()
      .then(setD)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'تعذّر التحميل'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Wide><Spinner /></Wide>
  if (error || !d)
    return (
      <Wide>
        <div className="mt-space-xl">
          <InlineError message={error ?? 'غير متاح'} />
        </div>
      </Wide>
    )

  const flagged = d.communication.flagged_conversations

  return (
    <Wide>
      {/* Header */}
      <header className="flex flex-col gap-space-xs pb-space-lg mb-space-lg border-b border-surface-container-highest">
        <div className="flex items-center gap-space-xs font-small text-small text-secondary">
          <span>الإدارة والمالية</span>
          <span className="text-outline-variant">/</span>
          <span className="text-on-surface font-small-medium">لوحة التحليلات التنفيذية</span>
        </div>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-space-md">
          <div className="flex flex-col gap-space-xs max-w-2xl">
            <h1 className="font-display text-display text-on-surface font-medium tracking-tight">
              لوحة التحليلات التنفيذية
            </h1>
            <p className="font-body text-body text-on-surface-variant">
              نظرة شاملة على الإيرادات والتدفقات الائتمانية وكفاءة التوريد ومؤشرات العمليات. كل القيم
              بالجنيه المصري.
            </p>
          </div>
          <div className="flex items-center gap-space-sm self-start md:self-auto bg-surface-container-low px-space-md py-1.5">
            <span className="relative flex h-2 w-2">
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#0F6B3E]" />
            </span>
            <span className="font-small text-small text-secondary">بيانات لحظية من المنظومة</span>
          </div>
        </div>
      </header>

      {/* Section 1 — executive KPI matrix */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-space-md mb-space-xl">
        <Tile
          label="الإيرادات المحققة"
          value={formatMoney(d.sales.realized_revenue)}
          unit="ج.م"
          tone="signal"
          hint="تشمل المبيعات النقدية والمحصّلة من الآجل"
        />
        <Tile
          label="الذمم المستحقة القائمة"
          value={formatMoney(d.collection.outstanding)}
          unit="ج.م"
          tone="neutral"
          hint="إجمالي الأرصدة الآجلة غير المسدّدة"
        />
        <Tile
          label="الذمم المتعثّرة"
          value={formatMoney(d.collection.defaulted)}
          unit="ج.م"
          tone="error"
          hint="تم إيقاف التسهيلات والحدود تلقائياً"
        />
        <Tile
          label="مبيعات نقطة البيع غير المُرحَّلة"
          value={formatMoney(d.pos.unposted_total)}
          unit="ج.م"
          tone="neutral"
          hint="تنتظر الإقفال اليومي وتوليد القيد"
        />
        <Tile
          label="نقص وبنود إعادة الطلب بالمخزون"
          value={d.inventory.low_stock_slots}
          unit="أصناف حرجة"
          tone="warning"
          hint="الأرصدة الحالية أقل من حد الأمان التشغيلي"
        />
        <Tile
          label="المحادثات الخاضعة للوساطة"
          value={d.communication.open_conversations}
          unit="محادثة مفتوحة"
          tone={flagged > 0 ? 'error' : 'neutral'}
          hint="رصد محاولات مشاركة أرقام تواصل مباشرة"
          badge={
            flagged > 0 ? (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-full bg-[rgba(186,26,26,0.08)] text-error font-small text-[11px]">
                {flagged} محظورة للمراجعة
              </span>
            ) : undefined
          }
        />
      </section>

      {/* Section 2 — operations breakdown matrix */}
      <section className="mb-space-xl">
        <div className="flex items-center justify-between pb-space-sm mb-space-md">
          <h2 className="font-headline-1 text-headline-1 text-on-surface font-medium">
            تفكيك حالات دورة العمليات التشغيلية
          </h2>
          <span className="font-small text-small text-secondary">(التدفق اللحظي للمستودع والمالية)</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-space-md">
          <Breakdown title="طلبات التوريد" map={d.sales.orders_by_status} />
          <Breakdown title="الشحنات اللوجستية" map={d.logistics.shipments_by_status} />
          <Breakdown title="أوامر التصنيع (MO)" map={d.production.orders_by_status} />
          <Breakdown title="الذمم الائتمانية" map={d.collection.dues_by_status} />
        </div>
      </section>
    </Wide>
  )
}

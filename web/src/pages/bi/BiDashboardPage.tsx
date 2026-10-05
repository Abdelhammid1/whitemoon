import { useEffect, useState, type ReactNode } from 'react'
import { Wide } from '../../layouts/AppShell'
import { Spinner, InlineError, Card, Pill } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { getDashboard, type Dashboard } from '../../api/bi'
import { ApiError } from '../../api/client'
import { formatNumber } from '../../lib/format'

type Tone = 'signal' | 'warning' | 'error' | 'neutral'

const STATUS_AR: Record<string, string> = {
  draft: 'مسودة', pending: 'قيد الانتظار', confirmed: 'مؤكد ومقبول', fulfilled: 'تم التجهيز',
  cancelled: 'ملغى', rejected: 'مرفوض', scheduled: 'مجدولة للشحن', shipped: 'خرجت من المستودع',
  in_transit: 'في الطريق', delivered: 'تم التسليم', failed: 'فشل التسليم',
  in_progress: 'قيد التشغيل', completed: 'مكتمل', open: 'مفتوحة', partial: 'سداد جزئي',
  paid: 'مسدّدة', overdue: 'متأخرة', defaulted: 'متعثّرة', due: 'مستحقة',
}

const STATUS_TONE: Record<string, Tone> = {
  confirmed: 'signal', fulfilled: 'signal', delivered: 'signal', completed: 'signal', paid: 'signal',
  pending: 'warning', in_transit: 'warning', shipped: 'warning', in_progress: 'warning',
  scheduled: 'warning', partial: 'warning', overdue: 'warning', due: 'warning',
  cancelled: 'error', rejected: 'error', failed: 'error', defaulted: 'error',
  draft: 'neutral', open: 'neutral',
}

const BAR: Record<Tone, string> = {
  signal: 'bg-signal', warning: 'bg-warning', error: 'bg-danger', neutral: 'bg-primary/55',
}

/** Executive KPI tile: icon chip, label, large mono value, a quiet hint. */
function Tile({ label, value, unit, hint, tone = 'neutral', icon, accent, badge }: {
  label: string; value: ReactNode; unit?: string; hint: string
  tone?: Tone; icon: string; accent?: boolean; badge?: ReactNode
}) {
  const chip = accent ? 'bg-gold-weak text-gold' : 'bg-brand-weak text-primary'
  const hintCls = tone === 'error' ? 'text-danger' : tone === 'warning' ? 'text-warning' : 'text-secondary'
  return (
    <Card className="flex flex-col gap-space-md min-h-[158px]">
      <div className="flex items-start justify-between gap-space-sm">
        <span className={`w-10 h-10 rounded-xl flex items-center justify-center ${chip}`}>
          <Icon name={icon} size={20} />
        </span>
        {badge}
      </div>
      <div className="flex items-baseline gap-space-xs">
        <span className={`font-mono-medium text-display tracking-tight ${tone === 'error' ? 'text-danger' : 'text-on-surface'}`} dir="ltr">
          {value}
        </span>
        {unit && <span className={`font-small text-small ${tone === 'error' ? 'text-danger' : 'text-secondary'}`}>{unit}</span>}
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="font-body-medium text-body-medium text-on-surface">{label}</span>
        <span className={`font-small text-small ${hintCls}`}>{hint}</span>
      </div>
    </Card>
  )
}

/** Breakdown card: title + total, then a proportional bar per status (to scale). */
function Breakdown({ title, map }: { title: string; map: Record<string, number> }) {
  const entries = Object.entries(map)
  const total = entries.reduce((s, [, v]) => s + v, 0)
  const max = entries.reduce((m, [, v]) => Math.max(m, v), 0) || 1
  return (
    <Card className="flex flex-col">
      <div className="flex items-center justify-between pb-space-sm mb-space-md border-b border-surface-container-high">
        <span className="font-headline-2 text-headline-2 text-on-surface">{title}</span>
        <span className="font-mono-medium text-mono-medium text-secondary" dir="ltr">{total}</span>
      </div>
      {entries.length === 0 ? (
        <span className="font-small text-small text-secondary">—</span>
      ) : (
        <div className="flex flex-col gap-space-sm">
          {entries.map(([k, v]) => {
            const tone = STATUS_TONE[k] ?? 'neutral'
            return (
              <div key={k} className="flex flex-col gap-1">
                <div className="flex items-center justify-between font-small text-small">
                  <span className="text-secondary">{STATUS_AR[k] ?? k}</span>
                  <span className={`font-mono-body ${tone === 'error' ? 'text-danger' : 'text-on-surface'}`} dir="ltr">{v}</span>
                </div>
                <div className="h-1.5 rounded-pill bg-surface-container overflow-hidden">
                  <div className={`h-full rounded-pill ${BAR[tone]}`} style={{ width: `${Math.max(4, (v / max) * 100)}%` }} />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </Card>
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
    return <Wide><div className="mt-space-xl"><InlineError message={error ?? 'غير متاح'} /></div></Wide>

  const flagged = d.communication.flagged_conversations

  return (
    <Wide>
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-space-md">
        <div className="flex flex-col gap-space-xs max-w-2xl">
          <h1 className="font-display text-display text-on-surface font-medium tracking-tight">التحليلات التنفيذية</h1>
          <p className="font-body text-body text-on-surface-variant">
            نظرة شاملة على الإيرادات والتدفقات الائتمانية وكفاءة التوريد ومؤشرات العمليات — كل القيم بالجنيه المصري.
          </p>
        </div>
        <Pill tone="signal">● بيانات لحظية من المنظومة</Pill>
      </header>

      {/* KPI matrix */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-space-md mt-space-xl">
        <Tile icon="payments" accent label="الإيرادات المحققة" value={formatNumber(d.sales.realized_revenue)} unit="ج.م" tone="signal" hint="المبيعات النقدية والمحصّلة من الآجل" />
        <Tile icon="account_balance_wallet" label="الذمم المستحقة القائمة" value={formatNumber(d.collection.outstanding)} unit="ج.م" hint="إجمالي الأرصدة الآجلة غير المسدّدة" />
        <Tile icon="gpp_bad" label="الذمم المتعثّرة" value={formatNumber(d.collection.defaulted)} unit="ج.م" tone="error" hint="تم إيقاف التسهيلات تلقائياً" />
        <Tile icon="point_of_sale" label="نقطة البيع غير المُرحَّلة" value={formatNumber(d.pos.unposted_total)} unit="ج.م" hint="تنتظر الإقفال اليومي وتوليد القيد" />
        <Tile icon="inventory" label="نقص وإعادة الطلب" value={d.inventory.low_stock_slots} unit="أصناف حرجة" tone="warning" hint="الأرصدة أقل من حد الأمان التشغيلي" />
        <Tile icon="forum" label="المحادثات الخاضعة للوساطة" value={d.communication.open_conversations} unit="محادثة مفتوحة" tone={flagged > 0 ? 'error' : 'neutral'} hint="رصد محاولات مشاركة أرقام مباشرة"
          badge={flagged > 0 ? <Pill tone="error">{flagged} محظورة</Pill> : undefined} />
      </section>

      {/* Operations breakdown */}
      <section className="mt-space-xl">
        <div className="flex items-center justify-between mb-space-md">
          <h2 className="font-headline-1 text-headline-1 text-on-surface font-medium">تفكيك حالات دورة العمليات</h2>
          <span className="font-small text-small text-secondary">التدفق اللحظي للمستودع والمالية</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-space-md">
          <Breakdown title="طلبات التوريد" map={d.sales.orders_by_status} />
          <Breakdown title="الشحنات اللوجستية" map={d.logistics.shipments_by_status} />
          <Breakdown title="أوامر التصنيع" map={d.production.orders_by_status} />
          <Breakdown title="الذمم الائتمانية" map={d.collection.dues_by_status} />
        </div>
      </section>
    </Wide>
  )
}

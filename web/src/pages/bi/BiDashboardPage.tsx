import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Spinner, InlineError, SectionHeader, Pill } from '../../components/ui'
import { Mono } from '../../components/DataTable'
import { getDashboard, type Dashboard } from '../../api/bi'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

function Tile({ label, value, mono = true }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="rounded-xl bg-surface-container-lowest border border-surface-container-high p-space-md flex flex-col gap-space-xs">
      <span className="font-small text-small text-secondary">{label}</span>
      <span className="font-display text-headline-1 text-primary">{mono ? <Mono>{value}</Mono> : value}</span>
    </div>
  )
}

function StatusRow({ map }: { map: Record<string, number> }) {
  const entries = Object.entries(map)
  if (entries.length === 0) return <span className="font-body text-body text-secondary">—</span>
  return (
    <div className="flex flex-wrap gap-space-sm">
      {entries.map(([k, v]) => (
        <Pill key={k} tone="neutral">{k}: {v}</Pill>
      ))}
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
  if (error || !d) return <Wide><div className="mt-space-xl"><InlineError message={error ?? 'غير متاح'} /></div></Wide>

  return (
    <Wide>
      <PageTitle title="لوحة التحليلات التنفيذية" subtitle="المؤشرات الحرجة للمنظومة في شاشة واحدة. كل القيم بالجنيه المصري." />

      <section className="mt-space-xl">
        <SectionHeader title="المبيعات والتحصيل" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-space-md">
          <Tile label="الإيرادات المتحققة" value={formatMoney(d.sales.realized_revenue)} />
          <Tile label="الذمم المستحقة" value={formatMoney(d.collection.outstanding)} />
          <Tile label="الذمم المتعثّرة" value={formatMoney(d.collection.defaulted)} />
          <Tile label="نقص المخزون" value={d.inventory.low_stock_slots} />
        </div>
      </section>

      <section className="mt-[48px]">
        <SectionHeader title="العمليات" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-space-md">
          <Tile label="مبيعات POS غير مُرحَّلة" value={formatMoney(d.pos.unposted_total)} />
          <Tile label="محادثات مفتوحة" value={d.communication.open_conversations} />
          <Tile label="محادثات محظورة" value={d.communication.flagged_conversations} />
        </div>
      </section>

      <section className="mt-[48px] flex flex-col gap-space-lg">
        <div><SectionHeader title="الطلبات حسب الحالة" /><StatusRow map={d.sales.orders_by_status} /></div>
        <div><SectionHeader title="الشحنات حسب الحالة" /><StatusRow map={d.logistics.shipments_by_status} /></div>
        <div><SectionHeader title="أوامر التصنيع حسب الحالة" /><StatusRow map={d.production.orders_by_status} /></div>
        <div><SectionHeader title="الذمم حسب الحالة" /><StatusRow map={d.collection.dues_by_status} /></div>
      </section>
    </Wide>
  )
}

import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, Button, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import {
  reorderAlerts,
  reorderEscalate,
  ackReorderAlert,
  reorderCheck,
  type ReorderAlert,
} from '../../api/inventory'
import { ApiError } from '../../api/client'

/** Reorder escalation ladder (US-4.3): level → Arabic label + Pill tone. */
const LEVEL_AR: Record<number, { label: string; tone: 'neutral' | 'warning' | 'error' }> = {
  1: { label: 'مستوى ١ — تنبيه', tone: 'neutral' },
  2: { label: 'مستوى ٢ — مشرف المخزون', tone: 'warning' },
  3: { label: 'مستوى ٣ — مدير المشتريات', tone: 'warning' },
  4: { label: 'مستوى ٤ — الإدارة', tone: 'error' },
}

function payloadText(p: Record<string, unknown>): string {
  const product = p.product_id ?? p.sku ?? ''
  const avail = p.available ?? p.on_hand
  const point = p.reorder_point
  const bits: string[] = []
  if (product !== '') bits.push(`منتج ${String(product)}`)
  if (avail != null) bits.push(`متاح ${String(avail)}`)
  if (point != null) bits.push(`حد ${String(point)}`)
  return bits.join(' · ') || '—'
}

export function ReorderAlertsPage() {
  const toast = useToast()
  const [rows, setRows] = useState<ReorderAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [openOnly, setOpenOnly] = useState(true)
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const resp = await reorderAlerts(openOnly)
      setRows(resp.items)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { void load() }, [openOnly]) // eslint-disable-line react-hooks/exhaustive-deps

  async function onScan() {
    setBusy(true)
    try {
      const r = await reorderCheck()
      toast.success(`تم فتح ${r.created.length} تنبيه جديد.`)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الفحص')
    } finally {
      setBusy(false)
    }
  }

  async function onEscalate() {
    setBusy(true)
    try {
      const r = await reorderEscalate()
      toast.success(`تم تصعيد ${r.advanced} وإغلاق ${r.closed}.`)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل التصعيد')
    } finally {
      setBusy(false)
    }
  }

  async function onAck(id: number) {
    try {
      await ackReorderAlert(id)
      toast.success('تم استلام التنبيه.')
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الاستلام')
    }
  }

  const chip = (active: boolean) =>
    `px-2 py-0.5 rounded-full font-small text-small transition-colors ${active ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant hover:text-primary'}`

  return (
    <Wide>
      <div className="flex items-start justify-between">
        <PageTitle title="تنبيهات إعادة الطلب" subtitle="سلسلة التصعيد تتقدّم مستوى كل ٢٤ ساعة دون استلام." />
        <div className="flex gap-space-sm">
          <Button variant="secondary" onClick={onScan} disabled={busy} iconRight="search">فحص الآن</Button>
          <Button onClick={onEscalate} disabled={busy} iconRight="arrow_upward">تصعيد المتأخّر</Button>
        </div>
      </div>

      <PageHelp pageKey="reorder" />

      <div className="mt-space-xl flex gap-space-xs">
        <button className={chip(openOnly)} onClick={() => setOpenOnly(true)}>المفتوحة</button>
        <button className={chip(!openOnly)} onClick={() => setOpenOnly(false)}>الكل</button>
      </div>

      <Card padded={false} className="mt-space-lg overflow-hidden">
        {loading ? <Spinner /> : (
          <DataTable rows={rows} rowKey={(a) => a.id} empty="لا توجد تنبيهات." columns={[
            { header: 'المستوى', cell: (a) => {
              const lv = LEVEL_AR[a.level] ?? { label: `مستوى ${a.level}`, tone: 'neutral' as const }
              return <Pill tone={lv.tone}>{lv.label}</Pill>
            } },
            { header: 'التفاصيل', cell: (a) => <span className="font-body text-body">{payloadText(a.payload)}</span> },
            { header: 'الحالة', cell: (a) => (a.acknowledged_at ? <Pill tone="neutral">مُستلم</Pill> : <Pill tone="warning">مفتوح</Pill>) },
            { header: 'رقم الرصيد', align: 'end', cell: (a) => <Mono>{a.stock_balance_id}</Mono> },
            { header: '', align: 'end', cell: (a) => (a.acknowledged_at ? null : (
              <Button variant="secondary" onClick={() => onAck(a.id)}>استلام</Button>
            )) },
          ]} />
        )}
      </Card>
    </Wide>
  )
}

import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, SectionHeader, Spinner, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import {
  getTransfer,
  issueTransfer,
  listTransfersPlanned,
  receiveTransfer,
  type TransferOrder,
} from '../../api/inventory'
import { ApiError } from '../../api/client'

const LOC_AR: Record<string, string> = {
  supplier: 'مخزن المورد', channel_partner: 'عهدة وكيل/فرع', in_transit: 'في الطريق', customer_hold: 'حجز عميل',
}
const STATUS: Record<string, { ar: string; tone: 'signal' | 'warning' | 'neutral' | 'error' }> = {
  draft: { ar: 'مسودة', tone: 'neutral' },
  issued: { ar: 'صادر (قيد النقل)', tone: 'warning' },
  received: { ar: 'مستلم', tone: 'signal' },
  cancelled: { ar: 'ملغي', tone: 'error' },
}

export function TransfersPage() {
  const toast = useToast()
  const [lookupId, setLookupId] = useState('')
  const [order, setOrder] = useState<TransferOrder | null>(null)
  const [busy, setBusy] = useState(false)
  const [rows, setRows] = useState<TransferOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await listTransfersPlanned()
      setRows(r.items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر تحميل الإذون')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function onLookup(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try { setOrder(await getTransfer(Number(lookupId))) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'لم يُعثر على الإذن'); setOrder(null) }
    finally { setBusy(false) }
  }

  async function act(fn: (id: number) => Promise<TransferOrder>, msg: string) {
    if (!order) return
    setBusy(true)
    try { setOrder(await fn(order.id)); toast.success(msg); await load() }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشلت العملية') }
    finally { setBusy(false) }
  }

  return (
    <Wide>
      <PageTitle title="إذون التحويل" subtitle="كل حركة بضاعة موثّقة بإذن تحويل وقيد محاسبي مرتبط." />

      <form onSubmit={onLookup} className="mt-space-xl flex items-end gap-space-md">
        <div className="w-56"><Field label="استعراض إذن برقمه" dir="ltr" mono inputMode="numeric" value={lookupId} onChange={(e) => setLookupId(e.target.value)} /></div>
        <Button variant="primary" type="submit" disabled={busy || !lookupId}>عرض</Button>
      </form>

      {order && (
        <section className="mt-space-xl border-t border-surface-container-high pt-space-lg">
          <div className="flex flex-wrap items-center gap-space-md">
            <Mono className="font-mono-medium">{order.number}</Mono>
            <Pill tone={STATUS[order.status]?.tone ?? 'neutral'}>{STATUS[order.status]?.ar ?? order.status}</Pill>
            <span className="font-body text-body text-secondary">
              من: {LOC_AR[order.from_location_type]} ← إلى: {LOC_AR[order.to_location_type]}
            </span>
          </div>

          <div className="mt-space-md">
            <DataTable rows={order.lines} rowKey={(l) => l.product_id} columns={[
              { header: 'رقم المنتج', cell: (l) => <Mono>{l.product_id}</Mono> },
              { header: 'الكمية', align: 'end', cell: (l) => <Mono>{l.qty}</Mono> },
              { header: 'التكلفة', align: 'end', cell: (l) => <Mono>{l.unit_cost}</Mono> },
            ]} />
          </div>

          <div className="mt-space-lg flex flex-col gap-space-sm">
            <div className="flex items-center gap-space-sm font-small text-small text-secondary">أُنشئ الإذن</div>
            {order.issue_entry_id && <div className="flex items-center gap-space-sm font-small text-small text-secondary">صدر — القيد <Mono>JV #{order.issue_entry_id}</Mono></div>}
            {order.receive_entry_id && <div className="flex items-center gap-space-sm font-small text-small text-secondary">استُلم — القيد <Mono>JV #{order.receive_entry_id}</Mono></div>}
          </div>

          <div className="mt-space-lg flex justify-end">
            {order.status === 'draft' && <Button variant="primary" onClick={() => act(issueTransfer, 'تم إصدار الإذن.')} disabled={busy}>إصدار</Button>}
            {order.status === 'issued' && <Button variant="primary" onClick={() => act(receiveTransfer, 'تم تأكيد الاستلام.')} disabled={busy}>تأكيد الاستلام</Button>}
          </div>
        </section>
      )}

      <section className="mt-[48px]">
        <SectionHeader title="قائمة الإذون" />
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : (
          <DataTable
            rows={rows}
            rowKey={(o) => o.id}
            onRowClick={(o) => { setOrder(o); setLookupId(String(o.id)) }}
            empty="لا توجد إذون تحويل بعد."
            columns={[
              { header: 'رقم الإذن', cell: (o) => <Mono>{o.number}</Mono> },
              { header: 'المسار', cell: (o) => <span className="font-body text-body text-secondary">{LOC_AR[o.from_location_type]} ← {LOC_AR[o.to_location_type]}</span> },
              { header: 'عدد الأصناف', align: 'center', cell: (o) => <Mono>{o.lines.length}</Mono> },
              { header: 'الحالة', align: 'center', cell: (o) => <Pill tone={STATUS[o.status]?.tone ?? 'neutral'}>{STATUS[o.status]?.ar ?? o.status}</Pill> },
            ]}
          />
        )}
      </section>
    </Wide>
  )
}

import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, SectionHeader, Spinner, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import {
  createTransfer,
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

const LOC_TYPES = ['supplier', 'channel_partner', 'in_transit', 'customer_hold']

interface LineDraft { product_id: string; qty: string; unit_cost: string }
const EMPTY_LINE: LineDraft = { product_id: '', qty: '', unit_cost: '' }
const EMPTY_CREATE = {
  supplier_id: '', from_location_type: 'supplier', from_location_id: '',
  to_location_type: 'channel_partner', to_location_id: '',
}

export function TransfersPage() {
  const toast = useToast()
  const [lookupId, setLookupId] = useState('')
  const [order, setOrder] = useState<TransferOrder | null>(null)
  const [busy, setBusy] = useState(false)
  const [rows, setRows] = useState<TransferOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_CREATE)
  const [lines, setLines] = useState<LineDraft[]>([{ ...EMPTY_LINE }])

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

  const validLines = lines.filter((l) => l.product_id && l.qty && l.unit_cost)
  const canCreate = Boolean(form.supplier_id) && validLines.length > 0

  async function onCreate() {
    setBusy(true)
    try {
      const created = await createTransfer({
        supplier_id: Number(form.supplier_id),
        from_location_type: form.from_location_type,
        ...(form.from_location_id ? { from_location_id: Number(form.from_location_id) } : {}),
        to_location_type: form.to_location_type,
        ...(form.to_location_id ? { to_location_id: Number(form.to_location_id) } : {}),
        lines: validLines.map((l) => ({ product_id: Number(l.product_id), qty: l.qty, unit_cost: l.unit_cost })),
      })
      toast.success(`تم إنشاء الإذن ${created.number}.`)
      setCreateOpen(false)
      setForm(EMPTY_CREATE)
      setLines([{ ...EMPTY_LINE }])
      setOrder(created)
      setLookupId(String(created.id))
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الإنشاء')
    } finally {
      setBusy(false)
    }
  }

  const selectCls =
    'bg-transparent border-b border-surface-container-high py-2 font-body text-body focus:outline-none focus:border-primary'

  return (
    <Wide>
      <div className="flex items-start justify-between">
        <PageTitle title="إذون التحويل" subtitle="كل حركة بضاعة موثّقة بإذن تحويل وقيد محاسبي مرتبط." />
        <Button variant="primary" onClick={() => { setForm(EMPTY_CREATE); setLines([{ ...EMPTY_LINE }]); setCreateOpen(true) }} iconRight="add">إذن تحويل جديد</Button>
      </div>

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

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="إذن تحويل جديد" footer={
        <>
          <Button onClick={() => setCreateOpen(false)}>إلغاء</Button>
          <Button variant="primary" onClick={onCreate} disabled={busy || !canCreate}>إنشاء (مسودة)</Button>
        </>
      }>
        <div className="flex flex-col gap-space-md">
          <Field label="رقم المورد" dir="ltr" mono inputMode="numeric" value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })} required />
          <div className="grid grid-cols-2 gap-space-md">
            <div className="flex flex-col">
              <label className="font-small text-small text-secondary mb-1">من موقع</label>
              <select className={selectCls} value={form.from_location_type} onChange={(e) => setForm({ ...form, from_location_type: e.target.value })}>
                {LOC_TYPES.map((l) => <option key={l} value={l}>{LOC_AR[l]}</option>)}
              </select>
            </div>
            <Field label="رقم الموقع المصدر (اختياري)" dir="ltr" mono inputMode="numeric" value={form.from_location_id} onChange={(e) => setForm({ ...form, from_location_id: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-space-md">
            <div className="flex flex-col">
              <label className="font-small text-small text-secondary mb-1">إلى موقع</label>
              <select className={selectCls} value={form.to_location_type} onChange={(e) => setForm({ ...form, to_location_type: e.target.value })}>
                {LOC_TYPES.map((l) => <option key={l} value={l}>{LOC_AR[l]}</option>)}
              </select>
            </div>
            <Field label="رقم الموقع الوجهة (اختياري)" dir="ltr" mono inputMode="numeric" value={form.to_location_id} onChange={(e) => setForm({ ...form, to_location_id: e.target.value })} />
          </div>

          <div className="border-t border-surface-container-high pt-space-md flex flex-col gap-space-sm">
            <div className="flex items-center justify-between">
              <span className="font-body-medium text-body-medium text-primary">الأصناف</span>
              <button type="button" className="font-small text-small text-primary hover:underline" onClick={() => setLines((ls) => [...ls, { ...EMPTY_LINE }])}>+ إضافة صنف</button>
            </div>
            {lines.map((l, i) => (
              <div key={i} className="grid grid-cols-[1fr_1fr_1fr_auto] items-end gap-space-sm">
                <Field label="المنتج" dir="ltr" mono inputMode="numeric" value={l.product_id} onChange={(e) => setLines((ls) => ls.map((x, j) => j === i ? { ...x, product_id: e.target.value } : x))} />
                <Field label="الكمية" dir="ltr" mono inputMode="decimal" value={l.qty} onChange={(e) => setLines((ls) => ls.map((x, j) => j === i ? { ...x, qty: e.target.value } : x))} />
                <Field label="التكلفة" dir="ltr" mono inputMode="decimal" value={l.unit_cost} onChange={(e) => setLines((ls) => ls.map((x, j) => j === i ? { ...x, unit_cost: e.target.value } : x))} />
                <button type="button" className="pb-2 text-secondary hover:text-[#B3261E] disabled:opacity-30" disabled={lines.length === 1} onClick={() => setLines((ls) => ls.filter((_, j) => j !== i))}>حذف</button>
              </div>
            ))}
          </div>
        </div>
      </Modal>
    </Wide>
  )
}

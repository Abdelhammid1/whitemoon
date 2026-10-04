import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Pill, SectionHeader, Spinner, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { advanceMO, cancelMO, completeMO, getMO, type ManufacturingOrder } from '../../api/production'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

const STATUS_AR: Record<string, string> = { draft: 'مسودة', in_progress: 'قيد التنفيذ', completed: 'مكتمل', cancelled: 'ملغى' }

export function ProductionDetailPage() {
  const { id } = useParams()
  const moId = Number(id)
  const toast = useToast()
  const [mo, setMo] = useState<ManufacturingOrder | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setMo(await getMO(moId)) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [moId])
  useEffect(() => { void load() }, [load])

  async function run(fn: () => Promise<unknown>, msg: string) {
    setBusy(true)
    try { await fn(); toast.success(msg); await load() }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشلت العملية') }
    finally { setBusy(false) }
  }

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error || !mo) return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>

  const allDone = mo.stages.every((s) => s.status === 'done')
  const open = mo.status === 'draft' || mo.status === 'in_progress'

  return (
    <Narrow>
      <PageTitle title={`أمر تصنيع ${mo.number}`} />
      <div className="mt-space-sm flex items-center gap-space-sm">
        <Pill tone={mo.status === 'completed' ? 'signal' : mo.status === 'cancelled' ? 'error' : 'warning'}>{STATUS_AR[mo.status] ?? mo.status}</Pill>
        <span className="font-body text-body text-secondary">منتج <Mono>#{mo.output_product_id}</Mono> — كمية <Mono>{mo.output_qty}</Mono></span>
        {mo.journal_entry_id && <span className="font-mono-body text-mono-body text-secondary">القيد JV #{mo.journal_entry_id}</span>}
      </div>

      <section className="mt-space-xl">
        <SectionHeader title="المراحل" />
        <div className="flex flex-col gap-space-xs">
          {mo.stages.map((s) => (
            <div key={s.seq} className="flex items-center justify-between py-space-sm border-b border-surface-container-high">
              <span className="font-body text-body">{s.seq}. {s.name}</span>
              <Pill tone={s.status === 'done' ? 'signal' : 'neutral'}>{s.status === 'done' ? 'تم' : 'معلّق'}</Pill>
            </div>
          ))}
        </div>
        {open && !allDone && <Button className="mt-space-md" disabled={busy} onClick={() => run(() => advanceMO(mo.id), 'تم إتمام المرحلة.')}>إتمام المرحلة التالية</Button>}
      </section>

      <section className="mt-[48px]">
        <SectionHeader title="الخامات" />
        <DataTable rows={mo.materials} rowKey={(m) => m.product_id} columns={[
          { header: 'الخامة', cell: (m) => <Mono>#{m.product_id}</Mono> },
          { header: 'الكمية', align: 'end', cell: (m) => <Mono>{m.qty}</Mono> },
          { header: 'التكلفة', align: 'end', cell: (m) => <Mono>{formatMoney(m.unit_cost)}</Mono> },
        ]} />
        <div className="mt-space-md flex items-center justify-between">
          <span className="font-small text-small text-secondary">إجمالي تكلفة الخامات</span>
          <span className="font-body-medium"><Mono>{formatMoney(mo.total_material_cost)}</Mono> ج.م</span>
        </div>
      </section>

      {open && (
        <section className="mt-[48px] flex justify-end gap-space-sm">
          <Button variant="destructive" disabled={busy} onClick={() => run(() => cancelMO(mo.id), 'أُلغي الأمر.')}>إلغاء الأمر</Button>
          <Button variant="primary" disabled={busy || !allDone}
            onClick={() => run(() => completeMO(mo.id), 'أُغلق الأمر — خُصمت الخامات وأُضيف المنتج.')}>
            إغلاق الأمر
          </Button>
        </section>
      )}
    </Narrow>
  )
}

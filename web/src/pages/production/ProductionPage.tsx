import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, InlineError, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { createMO, listMOs, type ManufacturingOrder } from '../../api/production'
import { useAuth } from '../../auth/AuthContext'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'
import { PageHelp } from '../../components/PageHelp'

const STATUS: Record<string, { ar: string; tone: 'signal' | 'warning' | 'neutral' | 'error' }> = {
  draft: { ar: 'مسودة', tone: 'neutral' },
  in_progress: { ar: 'قيد التنفيذ', tone: 'warning' },
  completed: { ar: 'مكتمل', tone: 'signal' },
  cancelled: { ar: 'ملغى', tone: 'error' },
}

export function ProductionPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [rows, setRows] = useState<ManufacturingOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [outPid, setOutPid] = useState('')
  const [outQty, setOutQty] = useState('')
  const [stages, setStages] = useState('قص, تجميع, تعبئة')
  const [mats, setMats] = useState([{ product_id: '', qty: '', unit_cost: '' }])

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setRows((await listMOs()).items) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  async function create() {
    setBusy(true)
    try {
      await createMO({
        owner_id: Number(user?.id),
        output_product_id: Number(outPid),
        output_qty: Number(outQty),
        materials: mats.filter((m) => m.product_id).map((m) => ({ product_id: Number(m.product_id), qty: Number(m.qty), unit_cost: Number(m.unit_cost) })),
        stages: stages.split(',').map((s) => s.trim()).filter(Boolean),
      })
      toast.success('أُنشئ أمر التصنيع.')
      setOpen(false); setOutPid(''); setOutQty(''); setMats([{ product_id: '', qty: '', unit_cost: '' }])
      await load()
    } catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر الإنشاء') }
    finally { setBusy(false) }
  }

  return (
    <Wide>
      <div className="flex items-center justify-between gap-space-md">
        <PageTitle title="أوامر التصنيع" subtitle="من الخامة إلى المنتج النهائي عبر مراحل، مع قيد تلقائي عند الإغلاق." />
        <Button variant="primary" onClick={() => setOpen(true)}>أمر تصنيع جديد</Button>
      </div>
      <PageHelp pageKey="production" />
      <div className="mt-space-xl">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : (
          <Card padded={false} className="overflow-hidden">
            <DataTable rows={rows} rowKey={(m) => m.id} onRowClick={(m) => navigate(`/production/${m.id}`)}
              empty="لا توجد أوامر." columns={[
                { header: 'الرقم', cell: (m) => <Mono>{m.number}</Mono> },
                { header: 'المنتج', cell: (m) => <Mono>#{m.output_product_id}</Mono> },
                { header: 'الكمية', align: 'end', cell: (m) => <Mono>{m.output_qty}</Mono> },
                { header: 'التكلفة', align: 'end', cell: (m) => <Mono>{formatMoney(m.total_material_cost)}</Mono> },
                { header: 'الحالة', align: 'center', cell: (m) => <Pill tone={STATUS[m.status]?.tone ?? 'neutral'}>{STATUS[m.status]?.ar ?? m.status}</Pill> },
              ]} />
          </Card>
        )}
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="أمر تصنيع جديد"
        footer={<><Button onClick={() => setOpen(false)}>إلغاء</Button>
          <Button variant="primary" disabled={busy || !outPid || !outQty} onClick={create}>إنشاء</Button></>}>
        <div className="flex flex-col gap-space-md">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            <Field label="المنتج النهائي (id)" dir="ltr" mono value={outPid} onChange={(e) => setOutPid(e.target.value)} />
            <Field label="الكمية" dir="ltr" mono value={outQty} onChange={(e) => setOutQty(e.target.value)} />
          </div>
          <Field label="المراحل (مفصولة بفواصل)" value={stages} onChange={(e) => setStages(e.target.value)} />
          <div className="flex flex-col gap-space-sm">
            <p className="font-small-medium text-small-medium text-secondary">الخامات</p>
            <div className="rounded-lg border border-surface-container-high p-space-md flex flex-col gap-space-sm">
              {mats.map((m, i) => (
                <div key={i} className="grid grid-cols-3 gap-space-sm">
                  <Field dir="ltr" mono placeholder="product id" value={m.product_id} onChange={(e) => setMats((s) => s.map((x, j) => j === i ? { ...x, product_id: e.target.value } : x))} />
                  <Field dir="ltr" mono placeholder="qty" value={m.qty} onChange={(e) => setMats((s) => s.map((x, j) => j === i ? { ...x, qty: e.target.value } : x))} />
                  <Field dir="ltr" mono placeholder="unit cost" value={m.unit_cost} onChange={(e) => setMats((s) => s.map((x, j) => j === i ? { ...x, unit_cost: e.target.value } : x))} />
                </div>
              ))}
              <Button variant="secondary" className="self-start" onClick={() => setMats((s) => [...s, { product_id: '', qty: '', unit_cost: '' }])}>+ خامة</Button>
            </div>
          </div>
        </div>
      </Modal>
    </Wide>
  )
}

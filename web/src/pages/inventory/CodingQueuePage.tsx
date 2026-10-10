import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, Card, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import { listCodingRequests, rejectCodingRequest, type AdminCodingRequest } from '../../api/inventory'
import { ApiError } from '../../api/client'
import { formatDateTime } from '../../lib/format'

const STATUS: Record<string, { ar: string; tone: 'signal' | 'warning' | 'error' | 'neutral' }> = {
  new: { ar: 'جديد', tone: 'warning' },
  in_review: { ar: 'قيد المراجعة', tone: 'neutral' },
  coded: { ar: 'تم التكويد', tone: 'signal' },
  rejected: { ar: 'مرفوض', tone: 'error' },
}

export function CodingQueuePage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [rows, setRows] = useState<AdminCodingRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(0)
  const [filter, setFilter] = useState('')

  async function load() {
    setLoading(true); setError(null)
    try { setRows((await listCodingRequests(filter || undefined)).items) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [filter]) // eslint-disable-line react-hooks/exhaustive-deps

  function createFrom(r: AdminCodingRequest) {
    // Pre-fill the product form; on save it links back + marks the request coded.
    navigate('/inventory/products/new', {
      state: {
        coding_request_id: r.id,
        name_ar: r.name,
        barcode: r.barcode ?? undefined,
        brand: r.brand ?? undefined,
        category: r.category ?? undefined,
        image_url: r.image_url ?? undefined,
      },
    })
  }

  async function reject(r: AdminCodingRequest) {
    const reason = window.prompt('سبب رفض الطلب (يظهر للمورد):', '')
    if (reason === null) return
    if (reason.trim().length < 3) { toast.error('اكتب سببًا واضحًا.'); return }
    setBusy(r.id)
    try { await rejectCodingRequest(r.id, reason.trim()); toast.success('رُفض الطلب.'); await load() }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر الرفض') }
    finally { setBusy(0) }
  }

  return (
    <Wide>
      <PageTitle title="طابور تكويد الأصناف" subtitle="طلبات الموردين لإضافة أصناف جديدة — راجع الباركود والاسم ثم أنشئ المنتج." />
      <PageHelp pageKey="coding-queue" />

      <div className="mt-space-md flex flex-wrap gap-space-xs">
        {['', 'new', 'in_review', 'coded', 'rejected'].map((s) => (
          <button key={s || 'all'} onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-lg border font-small text-small transition-colors ${
              filter === s ? 'border-primary bg-primary/10 text-primary' : 'border-surface-container-high text-secondary hover:text-primary'
            }`}>
            {s === '' ? 'الكل' : STATUS[s]?.ar ?? s}
          </button>
        ))}
      </div>

      <Card padded={false} className="mt-space-md overflow-hidden">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : (
          <DataTable rows={rows} rowKey={(r) => r.id} empty="لا توجد طلبات تكويد." columns={[
            { header: 'الصنف', cell: (r) => <span className="font-body-medium text-body-medium text-primary">{r.name}</span> },
            { header: 'الباركود', cell: (r) => r.barcode ? <Mono>{r.barcode}</Mono> : <span className="text-secondary">—</span> },
            { header: 'المورد', cell: (r) => <Mono>{r.supplier_id}</Mono> },
            { header: 'التاريخ', cell: (r) => <Mono>{formatDateTime(r.created_at)}</Mono> },
            { header: 'الحالة', align: 'center', cell: (r) => <Pill tone={STATUS[r.status]?.tone ?? 'neutral'}>{STATUS[r.status]?.ar ?? r.status}</Pill> },
            {
              header: '', align: 'end',
              cell: (r) => (r.status === 'new' || r.status === 'in_review') ? (
                <span className="flex gap-space-md justify-end items-center">
                  <button className="text-danger font-small-medium hover:underline disabled:opacity-40" disabled={busy === r.id} onClick={() => void reject(r)}>رفض</button>
                  <button className="text-primary font-small-medium hover:underline" onClick={() => createFrom(r)}>إنشاء منتج من الطلب</button>
                </span>
              ) : r.product_id ? <span className="font-small text-small text-secondary">منتج #{r.product_id}</span> : null,
            },
          ]} />
        )}
      </Card>
    </Wide>
  )
}

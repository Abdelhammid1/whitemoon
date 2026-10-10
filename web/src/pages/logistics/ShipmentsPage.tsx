import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, InlineError, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import { listShipments, setShipmentStatus, type Shipment } from '../../api/logistics'
import { ApiError } from '../../api/client'
import { formatDateTime } from '../../lib/format'

const STATUS_AR: Record<string, string> = {
  scheduled: 'بالجدول',
  shipped: 'تم الشحن',
  in_transit: 'في الطريق',
  delivered: 'تم التسليم',
  failed: 'فشل',
}

type Tone = 'signal' | 'warning' | 'error' | 'neutral'
const STATUS_TONE: Record<string, Tone> = {
  scheduled: 'neutral',
  shipped: 'signal',
  in_transit: 'warning',
  delivered: 'signal',
  failed: 'error',
}

// Only these three are driven through setShipmentStatus; 'delivered' goes
// through the confirmation-code flow on /logistics/deliver.
const STEP_AR: Record<string, string> = {
  shipped: 'تم الشحن',
  in_transit: 'في الطريق',
  failed: 'فشل',
}

const STATUS_OPTIONS = ['scheduled', 'shipped', 'in_transit', 'delivered', 'failed'] as const

export function ShipmentsPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [rows, setRows] = useState<Shipment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Draft filter inputs; applied to the query on submit.
  const [status, setStatus] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listShipments({
        status: status || undefined,
        from: from || undefined,
        to: to || undefined,
      })
      setRows(res.items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }, [status, from, to])

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function apply(e: FormEvent) {
    e.preventDefault()
    void load()
  }

  async function advance(s: Shipment, next: string) {
    setBusy(true)
    try {
      await setShipmentStatus(s.id, next)
      toast.success(`تم تحديث الحالة إلى «${STATUS_AR[next] ?? next}».`)
      await load()
    } catch (err) {
      // A 409 surfaces the server's Arabic "انتقال غير مسموح…" message.
      toast.error(err instanceof ApiError ? err.message : 'تعذّر تغيير الحالة')
    } finally {
      setBusy(false)
    }
  }

  function actions(s: Shipment) {
    const next = s.allowed_next ?? []
    const steps = next.filter((n) => n in STEP_AR)
    const canDeliver = next.includes('delivered')
    if (steps.length === 0 && !canDeliver) return <span className="text-secondary">—</span>
    return (
      <div className="flex flex-wrap gap-space-sm justify-end">
        {steps.map((n) => (
          <Button
            key={n}
            variant={n === 'failed' ? 'destructive' : 'secondary'}
            disabled={busy}
            onClick={() => advance(s, n)}
          >
            {STEP_AR[n]}
          </Button>
        ))}
        {canDeliver && (
          <Button variant="primary" iconRight="task_alt" disabled={busy} onClick={() => navigate('/logistics/deliver')}>
            تأكيد التسليم
          </Button>
        )}
      </div>
    )
  }

  return (
    <Wide>
      <PageTitle title="الشحنات" subtitle="تابع الشحنات وغيّر حالتها بالتسلسل الصحيح." />
      <PageHelp pageKey="shipments" />

      <Card className="mt-space-xl">
        <form onSubmit={apply} className="flex flex-wrap items-end gap-space-md">
          <div className="w-44">
            <label className="block font-small text-small text-secondary mb-1">الحالة</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full bg-transparent border-b border-surface-container-high py-1.5 font-body text-body text-primary focus:outline-none focus:border-primary"
            >
              <option value="">كل الحالات</option>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {STATUS_AR[s]}
                </option>
              ))}
            </select>
          </div>
          <div className="w-40">
            <Field label="من" type="date" dir="ltr" value={from} onChange={(e) => setFrom(e.target.value)} />
          </div>
          <div className="w-40">
            <Field label="إلى" type="date" dir="ltr" value={to} onChange={(e) => setTo(e.target.value)} />
          </div>
          <Button variant="primary" type="submit" iconRight="filter_alt" disabled={busy || loading}>
            تطبيق
          </Button>
        </form>

        <div className="-mx-space-lg -mb-space-lg mt-space-md border-t border-surface-container-high overflow-hidden">
          {loading ? (
            <Spinner />
          ) : error ? (
            <div className="p-space-lg">
              <InlineError message={error} />
            </div>
          ) : (
            <DataTable
              rows={rows}
              rowKey={(s) => s.id}
              empty="لا توجد شحنات مطابقة."
              columns={[
                { header: 'رقم الطلب', cell: (s) => <Mono>{s.order_id}</Mono> },
                {
                  header: 'الحالة',
                  cell: (s) => <Pill tone={STATUS_TONE[s.status] ?? 'neutral'}>{STATUS_AR[s.status] ?? s.status}</Pill>,
                },
                {
                  header: 'الناقل',
                  align: 'center',
                  cell: (s) => (s.carrier_type === 'internal' ? 'أسطول داخلي' : 'شحن خارجي'),
                },
                { header: 'تاريخ الإنشاء', align: 'center', cell: (s) => <Mono>{formatDateTime(s.created_at)}</Mono> },
                { header: 'الإجراءات', align: 'end', cell: actions },
              ]}
            />
          )}
        </div>
      </Card>
    </Wide>
  )
}

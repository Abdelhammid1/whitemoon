import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, EmptyState, InlineError, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { PageHelp } from '../../components/PageHelp'
import { adminListOrders, type AdminOrder, type OrderStatus } from '../../api/commerce'
import { ApiError } from '../../api/client'
import { formatDate, formatMoney } from '../../lib/format'

type Tone = 'warning' | 'brand' | 'signal' | 'error' | 'neutral'

const STATUS: Record<OrderStatus, { ar: string; tone: Tone }> = {
  pending: { ar: 'قيد الانتظار', tone: 'warning' },
  confirmed: { ar: 'مؤكد', tone: 'brand' },
  fulfilled: { ar: 'تم التجهيز', tone: 'signal' },
  cancelled: { ar: 'ملغي', tone: 'error' },
}

const STATUS_CHIPS: { value: '' | OrderStatus; label: string }[] = [
  { value: '', label: 'الكل' },
  { value: 'pending', label: 'قيد الانتظار' },
  { value: 'confirmed', label: 'مؤكد' },
  { value: 'fulfilled', label: 'تم التجهيز' },
  { value: 'cancelled', label: 'ملغي' },
]

interface Filters {
  status: '' | OrderStatus
  q: string
  customer_id: string
  date_from: string
  date_to: string
}
const EMPTY_FILTERS: Filters = { status: '', q: '', customer_id: '', date_from: '', date_to: '' }

export function AdminOrdersPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<'' | OrderStatus>('')
  const [q, setQ] = useState('')
  const [customerId, setCustomerId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [rows, setRows] = useState<AdminOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const runSearch = useCallback(async (f: Filters) => {
    setLoading(true)
    setError(null)
    try {
      const { items } = await adminListOrders({
        status: f.status || undefined,
        q: f.q.trim() || undefined,
        customer_id: f.customer_id.trim() || undefined,
        date_from: f.date_from || undefined,
        date_to: f.date_to || undefined,
      })
      setRows(items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void runSearch(EMPTY_FILTERS)
  }, [runSearch])

  function apply(e?: FormEvent) {
    e?.preventDefault()
    void runSearch({ status, q, customer_id: customerId, date_from: dateFrom, date_to: dateTo })
  }
  function pickStatus(s: '' | OrderStatus) {
    setStatus(s)
    void runSearch({ status: s, q, customer_id: customerId, date_from: dateFrom, date_to: dateTo })
  }

  return (
    <Wide>
      <PageTitle title="كل الطلبات" subtitle="كل طلبات العملاء مع البحث والفلترة وإدارة الحالة." />

      <PageHelp pageKey="admin-orders" />

      <Card className="mt-space-xl flex flex-col gap-space-md">
        <div className="flex flex-wrap items-center gap-space-xs">
          {STATUS_CHIPS.map((c) => (
            <button
              key={c.value || 'all'}
              type="button"
              onClick={() => pickStatus(c.value)}
              className={`px-space-md py-1.5 rounded-full font-small-medium text-small-medium transition-colors ${
                status === c.value
                  ? 'bg-primary text-on-primary shadow-card-sm'
                  : 'bg-surface-container-low text-secondary hover:bg-surface-container'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        <form onSubmit={apply} className="flex flex-col gap-space-md">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md">
            <Field
              label="رقم الطلب"
              dir="ltr"
              mono
              placeholder="ORD-…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <Field
              label="رقم العميل"
              dir="ltr"
              mono
              placeholder="#"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
            />
            <Field
              label="من تاريخ"
              type="date"
              dir="ltr"
              mono
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
            <Field
              label="إلى تاريخ"
              type="date"
              dir="ltr"
              mono
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
          <div className="flex justify-end">
            <Button type="submit" variant="primary" iconRight="search">
              تطبيق
            </Button>
          </div>
        </form>
      </Card>

      <div className="mt-space-xl">
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : rows.length === 0 ? (
          <EmptyState title="لا توجد طلبات مطابقة." description="جرّب تعديل الفلاتر أو مسح البحث." />
        ) : (
          <Card padded={false} className="overflow-hidden">
            <DataTable
              rows={rows}
              rowKey={(o) => o.id}
              onRowClick={(o) => navigate(`/orders/${o.id}`)}
              columns={[
                { header: 'رقم الطلب', cell: (o) => <Mono>{o.number}</Mono> },
                {
                  header: 'العميل',
                  cell: (o) =>
                    o.customer_name ?? <Mono>#{o.customer_id}</Mono>,
                },
                {
                  header: 'الحالة',
                  align: 'center',
                  cell: (o) => (
                    <Pill tone={STATUS[o.status]?.tone ?? 'neutral'}>
                      {STATUS[o.status]?.ar ?? o.status}
                    </Pill>
                  ),
                },
                {
                  header: 'الإجمالي',
                  align: 'end',
                  cell: (o) => (
                    <Mono>
                      {formatMoney(o.payment_mode === 'deferred' ? o.total_deferred : o.total_cash)}
                    </Mono>
                  ),
                },
                { header: 'التاريخ', align: 'end', cell: (o) => <Mono>{formatDate(o.placed_at)}</Mono> },
              ]}
            />
          </Card>
        )}
      </div>
    </Wide>
  )
}

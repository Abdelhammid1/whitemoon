import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, InlineError, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { listOrders, type Order } from '../../api/commerce'
import { ApiError } from '../../api/client'
import { formatDate, formatMoney } from '../../lib/format'

const STATUS: Record<string, { ar: string; tone: 'signal' | 'warning' | 'neutral' | 'error' }> = {
  pending: { ar: 'قيد الانتظار', tone: 'warning' },
  confirmed: { ar: 'مؤكد', tone: 'signal' },
  fulfilled: { ar: 'منفَّذ', tone: 'signal' },
  cancelled: { ar: 'ملغى', tone: 'error' },
}

export function OrdersPage() {
  const navigate = useNavigate()
  const [rows, setRows] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listOrders()
      .then((r) => setRows(r.items))
      .catch((err) => setError(err instanceof ApiError ? err.message : 'تعذّر التحميل'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <Wide>
      <PageTitle title="طلباتي" subtitle="كل طلباتك وحالتها اللحظية." />
      <div className="mt-space-xl">
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : (
          <Card padded={false} className="overflow-hidden">
            <DataTable
              rows={rows}
              rowKey={(o) => o.id}
              onRowClick={(o) => navigate(`/orders/${o.id}`)}
              empty="لا توجد طلبات بعد."
              columns={[
                { header: 'رقم الطلب', cell: (o) => <Mono>{o.number}</Mono> },
                { header: 'الدفع', cell: (o) => (o.payment_mode === 'deferred' ? 'آجل' : 'نقدي') },
                { header: 'الإجمالي', align: 'end', cell: (o) => <Mono>{formatMoney(o.payment_mode === 'deferred' ? o.total_deferred : o.total_cash)}</Mono> },
                { header: 'الحالة', align: 'center', cell: (o) => <Pill tone={STATUS[o.status]?.tone ?? 'neutral'}>{STATUS[o.status]?.ar ?? o.status}</Pill> },
                { header: 'التاريخ', align: 'end', cell: (o) => <Mono>{formatDate(o.placed_at)}</Mono> },
              ]}
            />
          </Card>
        )}
      </div>
    </Wide>
  )
}

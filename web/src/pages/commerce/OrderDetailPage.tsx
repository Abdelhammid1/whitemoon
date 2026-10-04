import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { getOrder, type Order } from '../../api/commerce'
import { ApiError } from '../../api/client'
import { formatDate, formatMoney } from '../../lib/format'

const STATUS_AR: Record<string, string> = {
  pending: 'قيد الانتظار', confirmed: 'مؤكد', fulfilled: 'منفَّذ', cancelled: 'ملغى',
}

export function OrderDetailPage() {
  const { id } = useParams()
  const [order, setOrder] = useState<Order | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getOrder(Number(id))
      .then(setOrder)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'تعذّر التحميل'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error || !order) return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>

  return (
    <Narrow>
      <PageTitle title={`طلب ${order.number}`} />
      <div className="mt-space-sm flex items-center gap-space-sm">
        <Pill tone={order.status === 'cancelled' ? 'error' : order.status === 'pending' ? 'warning' : 'signal'}>
          {STATUS_AR[order.status] ?? order.status}
        </Pill>
        <span className="font-body text-body text-secondary">{order.payment_mode === 'deferred' ? 'آجل' : 'نقدي'}</span>
        <span className="font-mono-body text-mono-body text-secondary">{formatDate(order.placed_at)}</span>
      </div>

      <div className="mt-space-xl">
        <DataTable
          rows={order.lines ?? []}
          rowKey={(l) => `${l.product_id}`}
          empty="لا توجد بنود."
          columns={[
            { header: 'المنتج', cell: (l) => <Mono>#{l.product_id}</Mono> },
            { header: 'الكمية', align: 'end', cell: (l) => <Mono>{l.qty}</Mono> },
            { header: 'سعر الوحدة', align: 'end', cell: (l) => <Mono>{formatMoney(l.unit_price)}</Mono> },
            { header: 'الإجمالي', align: 'end', cell: (l) => <Mono>{formatMoney(l.line_total)}</Mono> },
          ]}
        />
      </div>

      <div className="mt-space-lg flex items-center justify-between border-t border-surface-container-high pt-space-md">
        <span className="font-body-medium text-body-medium">الإجمالي</span>
        <span className="font-display text-headline-1 text-primary">
          <Mono>{formatMoney(order.payment_mode === 'deferred' ? order.total_deferred : order.total_cash)}</Mono> ج.م
        </span>
      </div>

      <div className="mt-space-lg">
        <Link to={`/orders/${order.id}/shipment`} className="font-body text-body text-primary hover:underline">
          تتبع الشحنة ↗
        </Link>
      </div>
    </Narrow>
  )
}

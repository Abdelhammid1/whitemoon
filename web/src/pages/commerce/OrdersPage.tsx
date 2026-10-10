import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, InlineError, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { listOrders, reorder, type Order } from '../../api/commerce'
import { ApiError } from '../../api/client'
import { useToast } from '../../components/Toast'
import { formatDateTime, formatMoney } from '../../lib/format'
import { PageHelp } from '../../components/PageHelp'

const STATUS: Record<string, { ar: string; tone: 'signal' | 'warning' | 'neutral' | 'error' }> = {
  pending: { ar: 'قيد الانتظار', tone: 'warning' },
  confirmed: { ar: 'مؤكد', tone: 'signal' },
  fulfilled: { ar: 'منفَّذ', tone: 'signal' },
  cancelled: { ar: 'ملغى', tone: 'error' },
}

export function OrdersPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const [rows, setRows] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(0)

  async function doReorder(id: number) {
    setBusy(id)
    try {
      const r = await reorder(id)
      const changed = r.warnings.filter((w) => w.reason === 'price_changed').length
      const gone = r.warnings.filter((w) => w.reason === 'unavailable').length
      let msg = `أُضيف ${r.added} صنف للسلة.`
      if (changed) msg += ` تغيّر سعر ${changed}.`
      if (gone) msg += ` ${gone} غير متاح.`
      toast.success(msg)
      navigate('/cart')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّرت إعادة الطلب')
    } finally { setBusy(0) }
  }

  useEffect(() => {
    listOrders()
      .then((r) => setRows(r.items))
      .catch((err) => setError(err instanceof ApiError ? err.message : 'تعذّر التحميل'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <Wide>
      <PageTitle title="طلباتي" subtitle="كل طلباتك وحالتها اللحظية." />
      <PageHelp pageKey="orders" />
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
                { header: 'التاريخ', align: 'end', cell: (o) => <Mono>{formatDateTime(o.placed_at)}</Mono> },
                {
                  header: '', align: 'end',
                  cell: (o) => o.status !== 'cancelled' ? (
                    <button
                      className="text-primary font-small-medium hover:underline disabled:opacity-40"
                      disabled={busy === o.id}
                      onClick={(e) => { e.stopPropagation(); void doReorder(o.id) }}
                    >
                      {busy === o.id ? '…' : 'اطلب مجددًا'}
                    </button>
                  ) : null,
                },
              ]}
            />
          </Card>
        )}
      </div>
    </Wide>
  )
}

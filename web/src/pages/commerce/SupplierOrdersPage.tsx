import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { supplierOrders, type SupplierOrderRow } from '../../api/commerce'
import { ApiError } from '../../api/client'

/** Sub-order status → Arabic label + Pill tone. Customer identity stays hidden:
 *  the supplier sees only their own fulfilment slice, never the buyer. */
const STATUS_AR: Record<string, { label: string; tone: 'signal' | 'warning' | 'error' | 'neutral' }> = {
  pending: { label: 'بانتظار التجهيز', tone: 'warning' },
  confirmed: { label: 'مؤكّد', tone: 'neutral' },
  preparing: { label: 'قيد التجهيز', tone: 'neutral' },
  shipped: { label: 'تم الشحن', tone: 'signal' },
  delivered: { label: 'تم التسليم', tone: 'signal' },
  cancelled: { label: 'ملغي', tone: 'error' },
}

function statusPill(s: string) {
  const m = STATUS_AR[s] ?? { label: s, tone: 'neutral' as const }
  return <Pill tone={m.tone}>{m.label}</Pill>
}

export function SupplierOrdersPage() {
  const toast = useToast()
  const [rows, setRows] = useState<SupplierOrderRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const resp = await supplierOrders()
        if (alive) setRows(resp.items)
      } catch (err) {
        if (alive) toast.error(err instanceof ApiError ? err.message : 'تعذّر التحميل')
      } finally {
        if (alive) setLoading(false)
      }
    })()
    return () => { alive = false }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Wide>
      <PageTitle title="طلبات واردة" subtitle="حصّتك من الطلبات فقط — هوية العميل غير ظاهرة." />

      <div className="mt-space-xl">
        {loading ? <Spinner /> : (
          <Card padded={false} className="overflow-hidden">
            <DataTable rows={rows} rowKey={(r) => r.sub_order_id} empty="لا توجد طلبات واردة." columns={[
              { header: 'رقم الطلب', cell: (r) => <Mono>{r.order_number}</Mono> },
              { header: 'حالة طلبك', cell: (r) => statusPill(r.sub_order_status) },
              { header: 'الأصناف', cell: (r) => (
                <span className="font-body text-body">
                  {r.lines?.length ? `${r.lines.length} صنف` : '—'}
                </span>
              ) },
              { header: 'الإجمالي', align: 'end', cell: (r) => <Mono>{r.subtotal ? `${r.subtotal} ج.م` : '—'}</Mono> },
            ]} />
          </Card>
        )}
      </div>
    </Wide>
  )
}

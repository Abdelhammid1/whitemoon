import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, InlineError, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { getSale, listSales, type PosSale } from '../../api/pos'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'
import { useToast } from '../../components/Toast'

const LOC_AR: Record<string, string> = {
  supplier: 'مخزن المورد', channel_partner: 'عهدة وكيل/فرع', branch: 'فرع', warehouse: 'مستودع',
}

export function PosSalesPage() {
  const toast = useToast()
  const [rows, setRows] = useState<PosSale[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detail, setDetail] = useState<PosSale | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    listSales()
      .then((r) => setRows(r.items))
      .catch((err) => setError(err instanceof ApiError ? err.message : 'تعذّر التحميل'))
      .finally(() => setLoading(false))
  }, [])

  async function openDetail(sale: PosSale) {
    setDetail(sale) // show cached row immediately, then refresh with full detail
    setDetailLoading(true)
    try {
      setDetail(await getSale(sale.id))
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر تحميل التفاصيل')
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <Wide>
      <PageTitle title="مبيعاتي" subtitle="مبيعات نقطة البيع التي سجّلتها وحالتها المحاسبية." />
      <div className="mt-space-xl">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : (
          <Card padded={false} className="overflow-hidden">
            <DataTable rows={rows} rowKey={(s) => s.id} onRowClick={(s) => void openDetail(s)} empty="لا توجد مبيعات." columns={[
              { header: 'الرقم', cell: (s) => <Mono>{s.number}</Mono> },
              { header: 'الأصناف', align: 'center', cell: (s) => <Mono>{s.lines.length}</Mono> },
              { header: 'الإجمالي', align: 'end', cell: (s) => <Mono>{formatMoney(s.total)}</Mono> },
              { header: 'الترحيل', align: 'center', cell: (s) => <Pill tone={s.posted ? 'signal' : 'warning'}>{s.posted ? 'مُرحَّل' : 'غير مُرحَّل'}</Pill> },
            ]} />
          </Card>
        )}
      </div>

      <Modal open={detail !== null} onClose={() => setDetail(null)} title={detail ? `فاتورة ${detail.number}` : ''}>
        {detail && (
          <div className="flex flex-col gap-space-md">
            <div className="flex flex-wrap items-center gap-space-sm">
              <Pill tone={detail.posted ? 'signal' : 'warning'}>{detail.posted ? 'مُرحَّل' : 'غير مُرحَّل'}</Pill>
              <span className="font-body text-body text-secondary">{LOC_AR[detail.location_type] ?? detail.location_type}</span>
              {detail.batch_id != null && <Mono className="text-secondary">دفعة #{detail.batch_id}</Mono>}
              {detailLoading && <Spinner label="تحديث…" />}
            </div>
            <DataTable rows={detail.lines} rowKey={(l, i) => `${l.product_id}-${i}`} empty="لا توجد أصناف." columns={[
              { header: 'المنتج', cell: (l) => <Mono>{l.product_id}</Mono> },
              { header: 'الكمية', align: 'center', cell: (l) => <Mono>{l.qty}</Mono> },
              { header: 'سعر الوحدة', align: 'end', cell: (l) => <Mono>{formatMoney(l.unit_price)}</Mono> },
              { header: 'الإجمالي', align: 'end', cell: (l) => <Mono>{formatMoney(l.line_total)}</Mono> },
            ]} />
            <div className="flex items-center justify-between border-t border-surface-container-high pt-space-md">
              <span className="font-body-medium text-body-medium text-primary">الإجمالي</span>
              <Mono className="text-primary">{formatMoney(detail.total)}</Mono>
            </div>
          </div>
        )}
      </Modal>
    </Wide>
  )
}

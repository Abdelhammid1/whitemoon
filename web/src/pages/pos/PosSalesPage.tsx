import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { listSales, type PosSale } from '../../api/pos'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

export function PosSalesPage() {
  const [rows, setRows] = useState<PosSale[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listSales()
      .then((r) => setRows(r.items))
      .catch((err) => setError(err instanceof ApiError ? err.message : 'تعذّر التحميل'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <Wide>
      <PageTitle title="مبيعاتي" subtitle="مبيعات نقطة البيع التي سجّلتها وحالتها المحاسبية." />
      <div className="mt-space-xl">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : (
          <DataTable rows={rows} rowKey={(s) => s.id} empty="لا توجد مبيعات." columns={[
            { header: 'الرقم', cell: (s) => <Mono>{s.number}</Mono> },
            { header: 'الأصناف', align: 'center', cell: (s) => <Mono>{s.lines.length}</Mono> },
            { header: 'الإجمالي', align: 'end', cell: (s) => <Mono>{formatMoney(s.total)}</Mono> },
            { header: 'الترحيل', align: 'center', cell: (s) => <Pill tone={s.posted ? 'signal' : 'warning'}>{s.posted ? 'مُرحَّل' : 'غير مُرحَّل'}</Pill> },
          ]} />
        )}
      </div>
    </Wide>
  )
}

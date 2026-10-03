import { useState } from 'react'
import { Card, CardHeader } from '../../../components/Card'
import { ReportFilterForm } from '../../../components/ReportFilterForm'
import { Table } from '../../../components/Table'
import { Badge } from '../../../components/Badge'
import { balanceSheet, type BalanceSheetResponse } from '../../../api/accounting'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatMoney } from '../../../lib/format'

export function BalanceSheetPage() {
  const toast = useToast()
  const [data, setData] = useState<BalanceSheetResponse | null>(null)
  const [busy, setBusy] = useState<boolean>(false)

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader title="المركز المالي" />
        <ReportFilterForm
          busy={busy}
          showPartner={false}
          showAccountPrefix={false}
          onRun={async (f) => {
            setBusy(true)
            try {
              setData(await balanceSheet(f))
            } catch (err) {
              toast.error(err instanceof ApiError ? err.message : 'فشل تشغيل التقرير')
            } finally {
              setBusy(false)
            }
          }}
        />
      </Card>

      {data && (
        <>
          <Card elevated>
            <div className="flex flex-wrap items-center justify-between gap-3 text-body text-ink">
              <span>الأصول: <span className="font-mono">{formatMoney(data.totals.assets)}</span></span>
              <span>الالتزامات: <span className="font-mono">{formatMoney(data.totals.liabilities)}</span></span>
              <span>حقوق الملكية: <span className="font-mono">{formatMoney(data.totals.equity)}</span></span>
              <Badge tone="neutral">{data.totals.balances ? 'A = L + E' : 'غير متوازن ⚠'}</Badge>
            </div>
          </Card>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Card>
              <CardHeader title="الأصول" />
              <Table
                rowKey={(r) => r.code}
                rows={data.assets}
                columns={[
                  { header: 'الكود', cell: (r) => <span className="font-mono">{r.code}</span> },
                  { header: 'الاسم', cell: (r) => r.name_ar },
                  { header: 'القيمة', align: 'end', cell: (r) => <span className="font-mono">{formatMoney(r.amount)}</span> },
                ]}
              />
            </Card>
            <Card>
              <CardHeader title="الالتزامات" />
              <Table
                rowKey={(r) => r.code}
                rows={data.liabilities}
                columns={[
                  { header: 'الكود', cell: (r) => <span className="font-mono">{r.code}</span> },
                  { header: 'الاسم', cell: (r) => r.name_ar },
                  { header: 'القيمة', align: 'end', cell: (r) => <span className="font-mono">{formatMoney(r.amount)}</span> },
                ]}
              />
            </Card>
            <Card>
              <CardHeader title="حقوق الملكية" />
              <Table
                rowKey={(r) => r.code}
                rows={data.equity}
                columns={[
                  { header: 'الكود', cell: (r) => <span className="font-mono">{r.code}</span> },
                  { header: 'الاسم', cell: (r) => r.name_ar },
                  { header: 'القيمة', align: 'end', cell: (r) => <span className="font-mono">{formatMoney(r.amount)}</span> },
                ]}
              />
            </Card>
          </div>
        </>
      )}
    </div>
  )
}

import { useState } from 'react'
import { Card, CardHeader } from '../../../components/Card'
import { ReportFilterForm } from '../../../components/ReportFilterForm'
import { Table } from '../../../components/Table'
import { incomeStatement, type IncomeStatementResponse } from '../../../api/accounting'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatMoney } from '../../../lib/format'

export function IncomeStatementPage() {
  const toast = useToast()
  const [data, setData] = useState<IncomeStatementResponse | null>(null)
  const [busy, setBusy] = useState<boolean>(false)

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader title="قائمة الدخل (P&L)" />
        <ReportFilterForm
          busy={busy}
          showAccountPrefix={false}
          showPartner={false}
          onRun={async (f) => {
            setBusy(true)
            try {
              setData(await incomeStatement(f))
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
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3 text-body text-ink">
              <span>الإيرادات: <span className="font-mono">{formatMoney(data.totals.revenue)}</span></span>
              <span>المصروفات: <span className="font-mono">{formatMoney(data.totals.expense)}</span></span>
              <span>صافي الدخل: <span className="font-mono">{formatMoney(data.totals.net_income)}</span></span>
            </div>
          </Card>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Card>
              <CardHeader title="الإيرادات" />
              <Table
                rowKey={(r) => r.code}
                rows={data.revenues}
                columns={[
                  { header: 'الكود', cell: (r) => <span className="font-mono">{r.code}</span>, width: '90px' },
                  { header: 'الاسم', cell: (r) => r.name_ar },
                  { header: 'القيمة', align: 'end', cell: (r) => <span className="font-mono">{formatMoney(r.amount)}</span> },
                ]}
              />
            </Card>
            <Card>
              <CardHeader title="المصروفات" />
              <Table
                rowKey={(r) => r.code}
                rows={data.expenses}
                columns={[
                  { header: 'الكود', cell: (r) => <span className="font-mono">{r.code}</span>, width: '90px' },
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

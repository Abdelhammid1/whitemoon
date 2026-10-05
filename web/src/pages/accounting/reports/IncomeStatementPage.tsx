import { useState } from 'react'
import { Narrow } from '../../../layouts/AppShell'
import { PageTitle } from '../../../components/ui'
import { ReportFilterForm } from '../../../components/ReportFilterForm'
import { DataTable, Mono } from '../../../components/DataTable'
import { incomeStatement, type ReportFilterBody, type IncomeStatementResponse } from '../../../api/accounting'
import { ReportExport } from '../../../components/ReportExport'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatMoney } from '../../../lib/format'

export function IncomeStatementPage() {
  const toast = useToast()
  const [data, setData] = useState<IncomeStatementResponse | null>(null)
  const [filter, setFilter] = useState<ReportFilterBody | null>(null)
  const [busy, setBusy] = useState(false)

  const cols = [
    { header: 'الكود', width: '90px', cell: (r: { code: string }) => <Mono>{r.code}</Mono> },
    { header: 'الاسم', cell: (r: { name_ar: string }) => <span className="font-body text-body">{r.name_ar}</span> },
    { header: 'القيمة', align: 'end' as const, cell: (r: { amount: string }) => <Mono>{formatMoney(r.amount)}</Mono> },
  ]

  return (
    <Narrow>
      <div className="flex items-center justify-between">
        <PageTitle title="قائمة الدخل" />
        <ReportExport path="/accounting/reports/income-statement" name="قائمة-الدخل" body={filter} disabled={!data || !filter} />
      </div>
      <div className="mt-space-xl">
        <ReportFilterForm busy={busy} showAccountPrefix={false} showPartner={false} onRun={async (f) => {
          setBusy(true)
          try { setData(await incomeStatement(f)); setFilter(f) }
          catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل التشغيل') }
          finally { setBusy(false) }
        }} />
      </div>
      {data && (
        <>
          <div className="mt-space-lg grid grid-cols-3 gap-space-md border-y border-surface-container-high py-space-md">
            <span className="font-body text-body text-secondary">الإيرادات: <Mono className="font-mono-medium">{formatMoney(data.totals.revenue)}</Mono></span>
            <span className="font-body text-body text-secondary">المصروفات: <Mono className="font-mono-medium">{formatMoney(data.totals.expense)}</Mono></span>
            <span className="font-body text-body text-on-surface">صافي الدخل: <Mono className="font-mono-medium">{formatMoney(data.totals.net_income)}</Mono></span>
          </div>
          <div className="mt-space-lg grid grid-cols-1 md:grid-cols-2 gap-space-xl">
            <div>
              <h3 className="font-headline-2 text-headline-2 text-primary font-medium pb-space-sm border-b border-surface-container-high">الإيرادات</h3>
              <div className="mt-space-sm"><DataTable rows={data.revenues} rowKey={(r) => r.code} columns={cols} /></div>
            </div>
            <div>
              <h3 className="font-headline-2 text-headline-2 text-primary font-medium pb-space-sm border-b border-surface-container-high">المصروفات</h3>
              <div className="mt-space-sm"><DataTable rows={data.expenses} rowKey={(r) => r.code} columns={cols} /></div>
            </div>
          </div>
        </>
      )}
    </Narrow>
  )
}

import { useState } from 'react'
import { Wide } from '../../../layouts/AppShell'
import { PageTitle, Pill } from '../../../components/ui'
import { ReportFilterForm } from '../../../components/ReportFilterForm'
import { ReportExport } from '../../../components/ReportExport'
import { DataTable, Mono } from '../../../components/DataTable'
import { trialBalance, type ReportFilterBody, type TrialBalanceResponse } from '../../../api/accounting'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatMoney } from '../../../lib/format'

export function TrialBalancePage() {
  const toast = useToast()
  const [data, setData] = useState<TrialBalanceResponse | null>(null)
  const [filter, setFilter] = useState<ReportFilterBody | null>(null)
  const [busy, setBusy] = useState(false)

  return (
    <Wide>
      <div className="flex items-center justify-between">
        <PageTitle title="ميزان المراجعة" />
        <ReportExport path="/accounting/reports/trial-balance" name="ميزان-المراجعة" body={filter} disabled={!data || !filter} />
      </div>
      <div className="mt-space-xl">
        <ReportFilterForm busy={busy} onRun={async (f) => {
          setBusy(true)
          try { setData(await trialBalance(f)); setFilter(f) }
          catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل التشغيل') }
          finally { setBusy(false) }
        }} />
      </div>

      {data && (
        <>
          <div className="mt-space-lg flex items-center gap-space-xl border-y border-surface-container-high py-space-md">
            <span className="font-body text-body text-secondary">إجمالي المدين: <Mono className="font-mono-medium">{formatMoney(data.totals.debit)}</Mono></span>
            <span className="font-body text-body text-secondary">إجمالي الدائن: <Mono className="font-mono-medium">{formatMoney(data.totals.credit)}</Mono></span>
            <Pill tone={data.totals.balanced ? 'signal' : 'error'}>{data.totals.balanced ? 'متوازن' : 'غير متوازن'}</Pill>
          </div>
          <div className="mt-space-md">
            <DataTable rows={data.rows} rowKey={(r) => r.code} columns={[
              { header: 'الكود', width: '90px', cell: (r) => <Mono>{r.code}</Mono> },
              { header: 'اسم الحساب', cell: (r) => <span className="font-body text-body">{r.name_ar}</span> },
              { header: 'النوع', cell: (r) => <Pill tone="neutral">{r.type}</Pill> },
              { header: 'مدين', align: 'end', cell: (r) => <Mono>{formatMoney(r.debit)}</Mono> },
              { header: 'دائن', align: 'end', cell: (r) => <Mono>{formatMoney(r.credit)}</Mono> },
              { header: 'الرصيد', align: 'end', cell: (r) => <Mono>{formatMoney(r.balance)}</Mono> },
            ]} />
          </div>
        </>
      )}
    </Wide>
  )
}

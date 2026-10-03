import { useState } from 'react'
import { Wide } from '../../../layouts/AppShell'
import { PageTitle, Pill } from '../../../components/ui'
import { ReportFilterForm } from '../../../components/ReportFilterForm'
import { DataTable, Mono } from '../../../components/DataTable'
import { balanceSheet, type BalanceSheetResponse } from '../../../api/accounting'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatMoney } from '../../../lib/format'

export function BalanceSheetPage() {
  const toast = useToast()
  const [data, setData] = useState<BalanceSheetResponse | null>(null)
  const [busy, setBusy] = useState(false)

  const cols = [
    { header: 'الكود', width: '80px', cell: (r: { code: string }) => <Mono>{r.code}</Mono> },
    { header: 'الاسم', cell: (r: { name_ar: string }) => <span className="font-body text-body">{r.name_ar}</span> },
    { header: 'القيمة', align: 'end' as const, cell: (r: { amount: string }) => <Mono>{formatMoney(r.amount)}</Mono> },
  ]

  return (
    <Wide>
      <PageTitle title="المركز المالي (الميزانية العمومية)" />
      <div className="mt-space-xl">
        <ReportFilterForm busy={busy} showAccountPrefix={false} showPartner={false} onRun={async (f) => {
          setBusy(true)
          try { setData(await balanceSheet(f)) }
          catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل التشغيل') }
          finally { setBusy(false) }
        }} />
      </div>
      {data && (
        <>
          <div className="mt-space-lg flex flex-wrap items-center gap-space-xl border-y border-surface-container-high py-space-md">
            <span className="font-body text-body text-secondary">الأصول: <Mono className="font-mono-medium">{formatMoney(data.totals.assets)}</Mono></span>
            <span className="font-body text-body text-secondary">الالتزامات: <Mono className="font-mono-medium">{formatMoney(data.totals.liabilities)}</Mono></span>
            <span className="font-body text-body text-secondary">حقوق الملكية: <Mono className="font-mono-medium">{formatMoney(data.totals.equity)}</Mono></span>
            <Pill tone={data.totals.balances ? 'signal' : 'error'}>A = L + E</Pill>
          </div>
          <div className="mt-space-lg grid grid-cols-1 md:grid-cols-3 gap-space-lg">
            <div><h3 className="font-headline-2 text-headline-2 text-primary font-medium pb-space-sm border-b border-surface-container-high">الأصول</h3><div className="mt-space-sm"><DataTable rows={data.assets} rowKey={(r) => r.code} columns={cols} /></div></div>
            <div><h3 className="font-headline-2 text-headline-2 text-primary font-medium pb-space-sm border-b border-surface-container-high">الالتزامات</h3><div className="mt-space-sm"><DataTable rows={data.liabilities} rowKey={(r) => r.code} columns={cols} /></div></div>
            <div><h3 className="font-headline-2 text-headline-2 text-primary font-medium pb-space-sm border-b border-surface-container-high">حقوق الملكية</h3><div className="mt-space-sm"><DataTable rows={data.equity} rowKey={(r) => r.code} columns={cols} /></div></div>
          </div>
        </>
      )}
    </Wide>
  )
}

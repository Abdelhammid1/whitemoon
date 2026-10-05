import { useState } from 'react'
import { Narrow } from '../../../layouts/AppShell'
import { PageTitle } from '../../../components/ui'
import { ReportFilterForm } from '../../../components/ReportFilterForm'
import { DataTable, Mono } from '../../../components/DataTable'
import { cashFlow, type ReportFilterBody, type CashFlowResponse } from '../../../api/accounting'
import { ReportExport } from '../../../components/ReportExport'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatMoney } from '../../../lib/format'

export function CashFlowPage() {
  const toast = useToast()
  const [data, setData] = useState<CashFlowResponse | null>(null)
  const [filter, setFilter] = useState<ReportFilterBody | null>(null)
  const [busy, setBusy] = useState(false)
  const cols = [
    { header: 'الكود', width: '80px', cell: (r: { code: string }) => <Mono>{r.code}</Mono> },
    { header: 'الاسم', cell: (r: { name_ar: string }) => <span className="font-body text-body">{r.name_ar}</span> },
    { header: 'القيمة', align: 'end' as const, cell: (r: { amount: string }) => <Mono>{formatMoney(r.amount)}</Mono> },
  ]
  return (
    <Narrow>
      <div className="flex items-center justify-between">
        <PageTitle title="قائمة التدفقات النقدية" />
        <ReportExport path="/accounting/reports/cash-flow" name="التدفقات-النقدية" body={filter} disabled={!data || !filter} />
      </div>
      <div className="mt-space-xl">
        <ReportFilterForm busy={busy} showAccountPrefix={false} showPartner={false} onRun={async (f) => {
          setBusy(true)
          try { setData(await cashFlow(f)); setFilter(f) }
          catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل التشغيل') }
          finally { setBusy(false) }
        }} />
      </div>
      {data && (
        <>
          <p className="mt-space-lg font-display text-display text-primary border-y border-surface-container-high py-space-md">
            صافي التغير النقدي: <Mono className="font-mono-medium">{formatMoney(data.net_cash_change)}</Mono>
          </p>
          <div className="mt-space-lg grid grid-cols-1 md:grid-cols-2 gap-space-xl">
            <div><h3 className="font-headline-2 text-headline-2 text-primary font-medium pb-space-sm border-b border-surface-container-high">مصادر النقد</h3><div className="mt-space-sm"><DataTable rows={data.sources} rowKey={(r) => r.code} columns={cols} empty="لا توجد حركات دخل." /></div></div>
            <div><h3 className="font-headline-2 text-headline-2 text-primary font-medium pb-space-sm border-b border-surface-container-high">استخدامات النقد</h3><div className="mt-space-sm"><DataTable rows={data.uses} rowKey={(r) => r.code} columns={cols} empty="لا توجد حركات صرف." /></div></div>
          </div>
        </>
      )}
    </Narrow>
  )
}

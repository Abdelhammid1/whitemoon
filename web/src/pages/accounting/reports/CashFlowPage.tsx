import { useState, type ReactNode } from 'react'
import { Wide } from '../../../layouts/AppShell'
import { PageTitle, Card } from '../../../components/ui'
import { Icon } from '../../../components/Icon'
import { ReportFilterForm } from '../../../components/ReportFilterForm'
import { DataTable, Mono } from '../../../components/DataTable'
import { cashFlow, type ReportFilterBody, type CashFlowResponse } from '../../../api/accounting'
import { ReportExport } from '../../../components/ReportExport'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatMoney } from '../../../lib/format'
import { PageHelp } from '../../../components/PageHelp'

/** KPI tile matching the executive dashboard: icon chip, large mono value, label. */
function Kpi({ icon, label, value, accent = false, tone = 'neutral' }: { icon: string; label: string; value: ReactNode; accent?: boolean; tone?: 'neutral' | 'error' }) {
  const chip = accent ? 'bg-gold-weak text-gold' : 'bg-brand-weak text-primary'
  const valueCls = tone === 'error' ? 'text-danger' : 'text-on-surface'
  return (
    <Card className="flex flex-col gap-space-md">
      <span className={`w-10 h-10 rounded-xl flex items-center justify-center ${chip}`}>
        <Icon name={icon} size={20} />
      </span>
      <span className={`font-mono-medium text-display tracking-tight ${valueCls}`} dir="ltr">{value}</span>
      <span className="font-body-medium text-body-medium text-on-surface">{label}</span>
    </Card>
  )
}

export function CashFlowPage() {
  const toast = useToast()
  const [data, setData] = useState<CashFlowResponse | null>(null)
  const [filter, setFilter] = useState<ReportFilterBody | null>(null)
  const [busy, setBusy] = useState(false)
  const cols = [
    { header: 'الكود', width: '80px', cell: (r: { code: string }) => <Mono>{r.code}</Mono> },
    { header: 'الاسم', cell: (r: { name_ar: string }) => <span className="font-body text-body text-on-surface">{r.name_ar}</span> },
    { header: 'القيمة', align: 'end' as const, cell: (r: { amount: string }) => <Mono>{formatMoney(r.amount)}</Mono> },
  ]

  const netNegative = data ? Number(data.net_cash_change) < 0 : false

  return (
    <Wide>
      <div className="flex items-center justify-between gap-space-md">
        <PageTitle title="قائمة التدفقات النقدية" subtitle="مصادر واستخدامات النقد وصافي التغير." />
        <ReportExport path="/accounting/reports/cash-flow" name="التدفقات-النقدية" body={filter} disabled={!data || !filter} />
      </div>

      <PageHelp pageKey="report-cashflow" />

      <Card className="mt-space-xl">
        <ReportFilterForm busy={busy} showAccountPrefix={false} showPartner={false} onRun={async (f) => {
          setBusy(true)
          try { setData(await cashFlow(f)); setFilter(f) }
          catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل التشغيل') }
          finally { setBusy(false) }
        }} />
      </Card>

      {data && (
        <>
          <section className="mt-space-xl grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-space-md">
            <Kpi icon="account_balance_wallet" accent label="صافي التغير النقدي" value={formatMoney(data.net_cash_change)} tone={netNegative ? 'error' : 'neutral'} />
          </section>

          <div className="mt-space-xl grid grid-cols-1 md:grid-cols-2 gap-space-md">
            <Card className="flex flex-col">
              <h3 className="font-headline-2 text-headline-2 text-on-surface pb-space-sm mb-space-sm border-b border-surface-container-high">مصادر النقد</h3>
              <DataTable rows={data.sources} rowKey={(r) => r.code} columns={cols} empty="لا توجد حركات دخل." />
            </Card>
            <Card className="flex flex-col">
              <h3 className="font-headline-2 text-headline-2 text-on-surface pb-space-sm mb-space-sm border-b border-surface-container-high">استخدامات النقد</h3>
              <DataTable rows={data.uses} rowKey={(r) => r.code} columns={cols} empty="لا توجد حركات صرف." />
            </Card>
          </div>
        </>
      )}
    </Wide>
  )
}

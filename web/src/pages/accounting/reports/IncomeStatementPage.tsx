import { useState, type ReactNode } from 'react'
import { Wide } from '../../../layouts/AppShell'
import { PageTitle, Card } from '../../../components/ui'
import { Icon } from '../../../components/Icon'
import { ReportFilterForm } from '../../../components/ReportFilterForm'
import { DataTable, Mono } from '../../../components/DataTable'
import { incomeStatement, type ReportFilterBody, type IncomeStatementResponse } from '../../../api/accounting'
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

export function IncomeStatementPage() {
  const toast = useToast()
  const [data, setData] = useState<IncomeStatementResponse | null>(null)
  const [filter, setFilter] = useState<ReportFilterBody | null>(null)
  const [busy, setBusy] = useState(false)

  const cols = [
    { header: 'الكود', width: '90px', cell: (r: { code: string }) => <Mono>{r.code}</Mono> },
    { header: 'الاسم', cell: (r: { name_ar: string }) => <span className="font-body text-body text-on-surface">{r.name_ar}</span> },
    { header: 'القيمة', align: 'end' as const, cell: (r: { amount: string }) => <Mono>{formatMoney(r.amount)}</Mono> },
  ]

  const netNegative = data ? Number(data.totals.net_income) < 0 : false

  return (
    <Wide>
      <div className="flex items-center justify-between gap-space-md">
        <PageTitle title="قائمة الدخل" subtitle="الإيرادات والمصروفات وصافي الدخل للفترة." />
        <ReportExport path="/accounting/reports/income-statement" name="قائمة-الدخل" body={filter} disabled={!data || !filter} />
      </div>

      <PageHelp pageKey="report-income" />

      <Card className="mt-space-xl">
        <ReportFilterForm busy={busy} showAccountPrefix={false} showPartner={false} onRun={async (f) => {
          setBusy(true)
          try { setData(await incomeStatement(f)); setFilter(f) }
          catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل التشغيل') }
          finally { setBusy(false) }
        }} />
      </Card>

      {data && (
        <>
          <section className="mt-space-xl grid grid-cols-1 sm:grid-cols-3 gap-space-md">
            <Kpi icon="trending_up" label="الإيرادات" value={formatMoney(data.totals.revenue)} />
            <Kpi icon="trending_down" label="المصروفات" value={formatMoney(data.totals.expense)} />
            <Kpi icon="savings" accent label="صافي الدخل" value={formatMoney(data.totals.net_income)} tone={netNegative ? 'error' : 'neutral'} />
          </section>

          <div className="mt-space-xl grid grid-cols-1 md:grid-cols-2 gap-space-md">
            <Card className="flex flex-col">
              <h3 className="font-headline-2 text-headline-2 text-on-surface pb-space-sm mb-space-sm border-b border-surface-container-high">الإيرادات</h3>
              <DataTable rows={data.revenues} rowKey={(r) => r.code} columns={cols} />
            </Card>
            <Card className="flex flex-col">
              <h3 className="font-headline-2 text-headline-2 text-on-surface pb-space-sm mb-space-sm border-b border-surface-container-high">المصروفات</h3>
              <DataTable rows={data.expenses} rowKey={(r) => r.code} columns={cols} />
            </Card>
          </div>
        </>
      )}
    </Wide>
  )
}

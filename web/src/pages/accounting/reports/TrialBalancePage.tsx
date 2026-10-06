import { useState, type ReactNode } from 'react'
import { Wide } from '../../../layouts/AppShell'
import { PageTitle, Pill, Card } from '../../../components/ui'
import { Icon } from '../../../components/Icon'
import { ReportFilterForm } from '../../../components/ReportFilterForm'
import { ReportExport } from '../../../components/ReportExport'
import { DataTable, Mono } from '../../../components/DataTable'
import { trialBalance, type ReportFilterBody, type TrialBalanceResponse } from '../../../api/accounting'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatMoney } from '../../../lib/format'
import { PageHelp } from '../../../components/PageHelp'

/** KPI tile matching the executive dashboard: icon chip, large mono value, label. */
function Kpi({ icon, label, value, accent = false }: { icon: string; label: string; value: ReactNode; accent?: boolean }) {
  const chip = accent ? 'bg-gold-weak text-gold' : 'bg-brand-weak text-primary'
  return (
    <Card className="flex flex-col gap-space-md">
      <span className={`w-10 h-10 rounded-xl flex items-center justify-center ${chip}`}>
        <Icon name={icon} size={20} />
      </span>
      <span className="font-mono-medium text-display tracking-tight text-on-surface" dir="ltr">{value}</span>
      <span className="font-body-medium text-body-medium text-on-surface">{label}</span>
    </Card>
  )
}

export function TrialBalancePage() {
  const toast = useToast()
  const [data, setData] = useState<TrialBalanceResponse | null>(null)
  const [filter, setFilter] = useState<ReportFilterBody | null>(null)
  const [busy, setBusy] = useState(false)

  return (
    <Wide>
      <div className="flex items-center justify-between gap-space-md">
        <PageTitle title="ميزان المراجعة" subtitle="أرصدة كل الحسابات لفترة محددة مع التحقق من التوازن." />
        <ReportExport path="/accounting/reports/trial-balance" name="ميزان-المراجعة" body={filter} disabled={!data || !filter} />
      </div>

      <PageHelp pageKey="report-trial-balance" />

      <Card className="mt-space-xl">
        <ReportFilterForm busy={busy} onRun={async (f) => {
          setBusy(true)
          try { setData(await trialBalance(f)); setFilter(f) }
          catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل التشغيل') }
          finally { setBusy(false) }
        }} />
      </Card>

      {data && (
        <>
          <section className="mt-space-xl grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-space-md">
            <Kpi icon="trending_up" label="إجمالي المدين" value={formatMoney(data.totals.debit)} />
            <Kpi icon="trending_down" label="إجمالي الدائن" value={formatMoney(data.totals.credit)} />
            <Card className="flex flex-col gap-space-md justify-between">
              <span className="w-10 h-10 rounded-xl flex items-center justify-center bg-brand-weak text-primary">
                <Icon name="balance" size={20} />
              </span>
              <div className="flex flex-col gap-space-sm items-start">
                <Pill tone={data.totals.balanced ? 'signal' : 'error'}>{data.totals.balanced ? 'متوازن' : 'غير متوازن'}</Pill>
                <span className="font-body-medium text-body-medium text-on-surface">حالة التوازن</span>
              </div>
            </Card>
          </section>

          <Card padded={false} className="mt-space-md overflow-hidden">
            <DataTable rows={data.rows} rowKey={(r) => r.code} columns={[
              { header: 'الكود', width: '90px', cell: (r) => <Mono>{r.code}</Mono> },
              { header: 'اسم الحساب', cell: (r) => <span className="font-body text-body text-on-surface">{r.name_ar}</span> },
              { header: 'النوع', cell: (r) => <Pill tone="neutral">{r.type}</Pill> },
              { header: 'مدين', align: 'end', cell: (r) => <Mono>{formatMoney(r.debit)}</Mono> },
              { header: 'دائن', align: 'end', cell: (r) => <Mono>{formatMoney(r.credit)}</Mono> },
              { header: 'الرصيد', align: 'end', cell: (r) => <Mono>{formatMoney(r.balance)}</Mono> },
            ]} />
          </Card>
        </>
      )}
    </Wide>
  )
}

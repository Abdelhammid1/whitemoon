import { useState, type ReactNode } from 'react'
import { Wide } from '../../../layouts/AppShell'
import { PageTitle, Pill, Card } from '../../../components/ui'
import { Icon } from '../../../components/Icon'
import { ReportFilterForm } from '../../../components/ReportFilterForm'
import { DataTable, Mono } from '../../../components/DataTable'
import { balanceSheet, type ReportFilterBody, type BalanceSheetResponse } from '../../../api/accounting'
import { ReportExport } from '../../../components/ReportExport'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatMoney } from '../../../lib/format'

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

export function BalanceSheetPage() {
  const toast = useToast()
  const [data, setData] = useState<BalanceSheetResponse | null>(null)
  const [filter, setFilter] = useState<ReportFilterBody | null>(null)
  const [busy, setBusy] = useState(false)

  const cols = [
    { header: 'الكود', width: '80px', cell: (r: { code: string }) => <Mono>{r.code}</Mono> },
    { header: 'الاسم', cell: (r: { name_ar: string }) => <span className="font-body text-body text-on-surface">{r.name_ar}</span> },
    { header: 'القيمة', align: 'end' as const, cell: (r: { amount: string }) => <Mono>{formatMoney(r.amount)}</Mono> },
  ]

  return (
    <Wide>
      <div className="flex items-center justify-between gap-space-md">
        <PageTitle title="المركز المالي (الميزانية العمومية)" subtitle="الأصول والالتزامات وحقوق الملكية كما في تاريخ." />
        <ReportExport path="/accounting/reports/balance-sheet" name="المركز-المالي" body={filter} disabled={!data || !filter} />
      </div>

      <Card className="mt-space-xl">
        <ReportFilterForm busy={busy} showAccountPrefix={false} showPartner={false} onRun={async (f) => {
          setBusy(true)
          try { setData(await balanceSheet(f)); setFilter(f) }
          catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل التشغيل') }
          finally { setBusy(false) }
        }} />
      </Card>

      {data && (
        <>
          <section className="mt-space-xl grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md">
            <Kpi icon="account_balance" label="الأصول" value={formatMoney(data.totals.assets)} />
            <Kpi icon="receipt_long" label="الالتزامات" value={formatMoney(data.totals.liabilities)} />
            <Kpi icon="savings" label="حقوق الملكية" value={formatMoney(data.totals.equity)} />
            <Card className="flex flex-col gap-space-md justify-between">
              <span className="w-10 h-10 rounded-xl flex items-center justify-center bg-brand-weak text-primary">
                <Icon name="balance" size={20} />
              </span>
              <div className="flex flex-col gap-space-sm items-start">
                <Pill tone={data.totals.balances ? 'signal' : 'error'}>A = L + E</Pill>
                <span className="font-body-medium text-body-medium text-on-surface">معادلة الميزانية</span>
              </div>
            </Card>
          </section>

          <div className="mt-space-xl grid grid-cols-1 md:grid-cols-3 gap-space-md">
            <Card className="flex flex-col">
              <h3 className="font-headline-2 text-headline-2 text-on-surface pb-space-sm mb-space-sm border-b border-surface-container-high">الأصول</h3>
              <DataTable rows={data.assets} rowKey={(r) => r.code} columns={cols} />
            </Card>
            <Card className="flex flex-col">
              <h3 className="font-headline-2 text-headline-2 text-on-surface pb-space-sm mb-space-sm border-b border-surface-container-high">الالتزامات</h3>
              <DataTable rows={data.liabilities} rowKey={(r) => r.code} columns={cols} />
            </Card>
            <Card className="flex flex-col">
              <h3 className="font-headline-2 text-headline-2 text-on-surface pb-space-sm mb-space-sm border-b border-surface-container-high">حقوق الملكية</h3>
              <DataTable rows={data.equity} rowKey={(r) => r.code} columns={cols} />
            </Card>
          </div>
        </>
      )}
    </Wide>
  )
}

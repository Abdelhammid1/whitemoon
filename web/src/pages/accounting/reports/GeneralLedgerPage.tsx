import { useState, type FormEvent } from 'react'
import { Wide } from '../../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Card } from '../../../components/ui'
import { Icon } from '../../../components/Icon'
import { DataTable, Mono } from '../../../components/DataTable'
import { generalLedger, type GeneralLedgerResponse } from '../../../api/accounting'
import { ReportExport } from '../../../components/ReportExport'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatDate, formatMoney, todayIso } from '../../../lib/format'
import { PageHelp } from '../../../components/PageHelp'

export function GeneralLedgerPage() {
  const toast = useToast()
  const [account, setAccount] = useState('1111')
  const [from, setFrom] = useState(() => {
    const d = new Date()
    return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10)
  })
  const [to, setTo] = useState(todayIso())
  const [data, setData] = useState<GeneralLedgerResponse | null>(null)
  const [busy, setBusy] = useState(false)

  async function onRun(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try { setData(await generalLedger(account, from, to)) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل التشغيل') }
    finally { setBusy(false) }
  }

  return (
    <Wide>
      <div className="flex items-center justify-between gap-space-md">
        <PageTitle title="الأستاذ العام" subtitle="حركة حساب واحد خلال فترة مع الرصيد الجاري." />
        <ReportExport
          method="GET"
          path={`/accounting/reports/general-ledger/${account}`}
          query={{ date_from: from, date_to: to }}
          name={`الأستاذ-${account}`}
          disabled={!data || !('account' in data)}
        />
      </div>

      <PageHelp pageKey="report-ledger" />

      <Card className="mt-space-xl">
        <form onSubmit={onRun} className="flex flex-wrap items-end gap-space-md">
          <div className="w-40"><Field label="كود الحساب" dir="ltr" mono value={account} onChange={(e) => setAccount(e.target.value)} required /></div>
          <div className="w-44"><Field label="من" type="date" dir="ltr" value={from} onChange={(e) => setFrom(e.target.value)} required /></div>
          <div className="w-44"><Field label="إلى" type="date" dir="ltr" value={to} onChange={(e) => setTo(e.target.value)} required /></div>
          <Button variant="primary" type="submit" disabled={busy}>{busy ? 'جار التشغيل…' : 'عرض'}</Button>
        </form>
      </Card>

      {data && 'account' in data && (
        <>
          <section className="mt-space-xl grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            <Card className="flex flex-col gap-space-md">
              <span className="w-10 h-10 rounded-xl flex items-center justify-center bg-brand-weak text-primary">
                <Icon name="menu_book" size={20} />
              </span>
              <div className="flex items-center gap-space-sm flex-wrap">
                <Mono className="font-mono-medium">{data.account.code}</Mono>
                <span className="font-body-medium text-body-medium text-on-surface">{data.account.name_ar}</span>
                <Pill tone="neutral">{data.account.type}</Pill>
              </div>
            </Card>
            <Card className="flex flex-col gap-space-md">
              <span className="w-10 h-10 rounded-xl flex items-center justify-center bg-gold-weak text-gold">
                <Icon name="account_balance_wallet" size={20} />
              </span>
              <span className="font-mono-medium text-display tracking-tight text-on-surface" dir="ltr">{formatMoney(data.closing_balance)}</span>
              <span className="font-body-medium text-body-medium text-on-surface">الرصيد الختامي</span>
            </Card>
          </section>

          <Card padded={false} className="mt-space-md overflow-hidden">
            <DataTable rows={data.rows} rowKey={(r) => `${r.entry_no}-${r.entry_date}`} empty="لا توجد حركات على هذا الحساب." columns={[
              { header: 'التاريخ', cell: (r) => <Mono>{formatDate(r.entry_date)}</Mono> },
              { header: 'رقم القيد', cell: (r) => <Mono>{r.entry_no}</Mono> },
              { header: 'البيان', cell: (r) => <span className="font-body text-body text-on-surface">{r.description}</span> },
              { header: 'مدين', align: 'end', cell: (r) => <Mono>{formatMoney(r.debit)}</Mono> },
              { header: 'دائن', align: 'end', cell: (r) => <Mono>{formatMoney(r.credit)}</Mono> },
              { header: 'الرصيد الجاري', align: 'end', cell: (r) => <Mono>{formatMoney(r.running_balance)}</Mono> },
            ]} />
          </Card>
        </>
      )}
    </Wide>
  )
}

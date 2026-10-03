import { useState, type FormEvent } from 'react'
import { Wide } from '../../../layouts/AppShell'
import { PageTitle, Button, Field, Pill } from '../../../components/ui'
import { DataTable, Mono } from '../../../components/DataTable'
import { generalLedger, type GeneralLedgerResponse } from '../../../api/accounting'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatDate, formatMoney, todayIso } from '../../../lib/format'

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
      <PageTitle title="الأستاذ العام" subtitle="حركة حساب واحد خلال فترة." />
      <form onSubmit={onRun} className="mt-space-xl flex flex-wrap items-end gap-space-md">
        <div className="w-40"><Field label="كود الحساب" dir="ltr" mono value={account} onChange={(e) => setAccount(e.target.value)} required /></div>
        <div className="w-44"><Field label="من" type="date" dir="ltr" value={from} onChange={(e) => setFrom(e.target.value)} required /></div>
        <div className="w-44"><Field label="إلى" type="date" dir="ltr" value={to} onChange={(e) => setTo(e.target.value)} required /></div>
        <Button variant="primary" type="submit" disabled={busy}>{busy ? 'جار التشغيل…' : 'عرض'}</Button>
      </form>

      {data && 'account' in data && (
        <>
          <div className="mt-space-lg flex flex-wrap items-center gap-space-xl border-y border-surface-container-high py-space-md">
            <Mono className="font-mono-medium">{data.account.code}</Mono>
            <span className="font-body text-body text-on-surface">{data.account.name_ar}</span>
            <Pill tone="neutral">{data.account.type}</Pill>
            <span className="font-body text-body text-secondary">الرصيد الختامي: <Mono className="font-mono-medium">{formatMoney(data.closing_balance)}</Mono></span>
          </div>
          <div className="mt-space-md">
            <DataTable rows={data.rows} rowKey={(r) => `${r.entry_no}-${r.entry_date}`} empty="لا توجد حركات على هذا الحساب." columns={[
              { header: 'التاريخ', cell: (r) => <Mono>{formatDate(r.entry_date)}</Mono> },
              { header: 'رقم القيد', cell: (r) => <Mono>{r.entry_no}</Mono> },
              { header: 'البيان', cell: (r) => <span className="font-body text-body">{r.description}</span> },
              { header: 'مدين', align: 'end', cell: (r) => <Mono>{formatMoney(r.debit)}</Mono> },
              { header: 'دائن', align: 'end', cell: (r) => <Mono>{formatMoney(r.credit)}</Mono> },
              { header: 'الرصيد الجاري', align: 'end', cell: (r) => <Mono>{formatMoney(r.running_balance)}</Mono> },
            ]} />
          </div>
        </>
      )}
    </Wide>
  )
}

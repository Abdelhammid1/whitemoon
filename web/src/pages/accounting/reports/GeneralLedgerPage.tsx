import { useState, type FormEvent } from 'react'
import { Card, CardHeader } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Button } from '../../../components/Button'
import { Table } from '../../../components/Table'
import { Badge } from '../../../components/Badge'
import { generalLedger, type GeneralLedgerResponse } from '../../../api/accounting'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatDate, formatMoney, todayIso } from '../../../lib/format'

export function GeneralLedgerPage() {
  const toast = useToast()
  const [account, setAccount] = useState<string>('1111')
  const [dateFrom, setDateFrom] = useState<string>(() => {
    const d = new Date()
    return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10)
  })
  const [dateTo, setDateTo] = useState<string>(todayIso())
  const [data, setData] = useState<GeneralLedgerResponse | null>(null)
  const [busy, setBusy] = useState<boolean>(false)

  async function onRun(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setBusy(true)
    try {
      setData(await generalLedger(account, dateFrom, dateTo))
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل تشغيل التقرير')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader title="الأستاذ العام" subtitle="لحساب واحد خلال فترة." />
        <form onSubmit={onRun} className="flex flex-wrap items-end gap-3">
          <div className="w-40">
            <Input
              label="كود الحساب"
              dir="ltr"
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              required
            />
          </div>
          <div className="w-44">
            <Input
              label="من"
              type="date"
              dir="ltr"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              required
            />
          </div>
          <div className="w-44">
            <Input
              label="إلى"
              type="date"
              dir="ltr"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              required
            />
          </div>
          <Button variant="filled" type="submit" disabled={busy}>
            {busy ? 'جار التشغيل…' : 'عرض'}
          </Button>
        </form>
      </Card>

      {data && (
        <>
          <Card elevated>
            <div className="flex flex-wrap items-center justify-between gap-3 text-body text-ink">
              <span className="font-mono">{data.account.code}</span>
              <span>{data.account.name_ar}</span>
              <Badge tone="muted">{data.account.type}</Badge>
              <span>
                الرصيد الختامي:{' '}
                <span className="font-mono">{formatMoney(data.closing_balance)}</span>
              </span>
            </div>
          </Card>
          <Card>
            <Table
              rowKey={(r) => `${r.entry_no}-${r.entry_date}`}
              rows={data.rows}
              empty="لا توجد حركات على هذا الحساب في الفترة."
              columns={[
                { header: 'التاريخ', cell: (r) => formatDate(r.entry_date) },
                { header: 'القيد', cell: (r) => <span className="font-mono">{r.entry_no}</span> },
                { header: 'الوصف', cell: (r) => r.description },
                { header: 'مدين', align: 'end', cell: (r) => <span className="font-mono">{formatMoney(r.debit)}</span> },
                { header: 'دائن', align: 'end', cell: (r) => <span className="font-mono">{formatMoney(r.credit)}</span> },
                { header: 'الرصيد الجاري', align: 'end', cell: (r) => <span className="font-mono">{formatMoney(r.running_balance)}</span> },
              ]}
            />
          </Card>
        </>
      )}
    </div>
  )
}

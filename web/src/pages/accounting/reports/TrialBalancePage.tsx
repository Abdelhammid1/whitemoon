import { useState } from 'react'
import { Card, CardHeader } from '../../../components/Card'
import { ReportFilterForm } from '../../../components/ReportFilterForm'
import { Table } from '../../../components/Table'
import { Badge } from '../../../components/Badge'
import { trialBalance, type TrialBalanceResponse } from '../../../api/accounting'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatMoney } from '../../../lib/format'

export function TrialBalancePage() {
  const toast = useToast()
  const [data, setData] = useState<TrialBalanceResponse | null>(null)
  const [busy, setBusy] = useState<boolean>(false)

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader title="ميزان المراجعة" subtitle="US-3.5" />
        <ReportFilterForm
          busy={busy}
          onRun={async (filter) => {
            setBusy(true)
            try {
              setData(await trialBalance(filter))
            } catch (err) {
              toast.error(err instanceof ApiError ? err.message : 'فشل تشغيل التقرير')
            } finally {
              setBusy(false)
            }
          }}
        />
      </Card>

      {data && (
        <>
          <Card elevated>
            <div className="flex items-center justify-between gap-4 text-body text-ink">
              <span>
                إجمالي المدين: <span className="font-mono">{formatMoney(data.totals.debit)}</span>
              </span>
              <span>
                إجمالي الدائن: <span className="font-mono">{formatMoney(data.totals.credit)}</span>
              </span>
              <Badge tone="neutral">
                {data.totals.balanced ? 'متوازن' : 'غير متوازن ⚠'}
              </Badge>
            </div>
          </Card>
          <Card>
            <Table
              rowKey={(r) => r.code}
              rows={data.rows}
              columns={[
                { header: 'الكود', cell: (r) => <span className="font-mono">{r.code}</span>, width: '90px' },
                { header: 'الاسم', cell: (r) => r.name_ar },
                { header: 'النوع', cell: (r) => <Badge tone="muted">{r.type}</Badge> },
                { header: 'مدين', align: 'end', cell: (r) => <span className="font-mono">{formatMoney(r.debit)}</span> },
                { header: 'دائن', align: 'end', cell: (r) => <span className="font-mono">{formatMoney(r.credit)}</span> },
                { header: 'الرصيد', align: 'end', cell: (r) => <span className="font-mono">{formatMoney(r.balance)}</span> },
              ]}
            />
          </Card>
        </>
      )}
    </div>
  )
}

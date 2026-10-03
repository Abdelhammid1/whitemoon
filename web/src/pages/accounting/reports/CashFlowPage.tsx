import { useState } from 'react'
import { Card, CardHeader } from '../../../components/Card'
import { ReportFilterForm } from '../../../components/ReportFilterForm'
import { Table } from '../../../components/Table'
import { cashFlow, type CashFlowResponse } from '../../../api/accounting'
import { ApiError } from '../../../api/client'
import { useToast } from '../../../components/Toast'
import { formatMoney } from '../../../lib/format'

export function CashFlowPage() {
  const toast = useToast()
  const [data, setData] = useState<CashFlowResponse | null>(null)
  const [busy, setBusy] = useState<boolean>(false)

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader title="التدفقات النقدية" />
        <ReportFilterForm
          busy={busy}
          showAccountPrefix={false}
          showPartner={false}
          onRun={async (f) => {
            setBusy(true)
            try {
              setData(await cashFlow(f))
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
            <p className="text-body text-ink">
              صافي التغيّر النقدي:{' '}
              <span className="font-mono">{formatMoney(data.net_cash_change)}</span>
            </p>
          </Card>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Card>
              <CardHeader title="المصادر (دخل نقدي)" />
              <Table
                rowKey={(r) => r.code}
                rows={data.sources}
                empty="لا توجد حركات دخل في الفترة."
                columns={[
                  { header: 'الكود', cell: (r) => <span className="font-mono">{r.code}</span> },
                  { header: 'الاسم', cell: (r) => r.name_ar },
                  { header: 'القيمة', align: 'end', cell: (r) => <span className="font-mono">{formatMoney(r.amount)}</span> },
                ]}
              />
            </Card>
            <Card>
              <CardHeader title="الاستخدامات (مصروف نقدي)" />
              <Table
                rowKey={(r) => r.code}
                rows={data.uses}
                empty="لا توجد حركات صرف في الفترة."
                columns={[
                  { header: 'الكود', cell: (r) => <span className="font-mono">{r.code}</span> },
                  { header: 'الاسم', cell: (r) => r.name_ar },
                  { header: 'القيمة', align: 'end', cell: (r) => <span className="font-mono">{formatMoney(r.amount)}</span> },
                ]}
              />
            </Card>
          </div>
        </>
      )}
    </div>
  )
}

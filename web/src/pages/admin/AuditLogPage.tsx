import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Spinner, InlineError, Pill, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { listAudit, type AuditRow } from '../../api/admin'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

export function AuditLogPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState<AuditRow[]>([])

  useEffect(() => {
    listAudit({ limit: 200 })
      .then((r) => setRows(r.items))
      .catch((err) => setError(err instanceof ApiError ? err.message : 'تعذّر التحميل'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <Wide>
      <PageTitle title="سجل التدقيق" subtitle="كل عملية حساسة في المنظومة موثّقة بالمنفِّذ والهدف والوقت." />
      <div className="mt-space-xl">
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : (
          <Card padded={false} className="overflow-hidden">
            <DataTable
              rows={rows}
              rowKey={(e) => e.id}
              empty="لا توجد أحداث مسجّلة بعد."
              columns={[
                { header: 'الوقت', cell: (e) => <Mono>{formatDate(e.at)}</Mono> },
                { header: 'الإجراء', cell: (e) => <Pill tone="neutral">{e.action}</Pill> },
                {
                  header: 'المنفِّذ',
                  align: 'center',
                  cell: (e) => <Mono>{e.actor_user_id ?? '—'}</Mono>,
                },
                {
                  header: 'الهدف',
                  cell: (e) => (
                    <span className="font-body text-body text-secondary">
                      {e.target_type ? `${e.target_type} ` : ''}
                      {e.target_id ? <Mono>#{e.target_id}</Mono> : '—'}
                    </span>
                  ),
                },
                {
                  header: 'السبب',
                  cell: (e) => (
                    <span className="font-body text-body text-secondary">{e.reason ?? '—'}</span>
                  ),
                },
              ]}
            />
          </Card>
        )}
      </div>
    </Wide>
  )
}

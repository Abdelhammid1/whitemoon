import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Spinner, InlineError, Pill, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { PageHelp } from '../../components/PageHelp'
import { listAudit, type AuditRow } from '../../api/admin'
import { ApiError } from '../../api/client'
import { formatDateTime } from '../../lib/format'

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
      <PageTitle title="سجل التدقيق" subtitle="كل عملية حساسة موثّقة بالمنفِّذ والهدف والوقت (بتوقيت مصر) وعنوان IP ونظام التشغيل." />
      <PageHelp pageKey="audit" />
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
                { header: 'الوقت (مصر)', cell: (e) => <Mono>{formatDateTime(e.at)}</Mono> },
                { header: 'الإجراء', cell: (e) => <Pill tone="neutral">{e.action}</Pill> },
                {
                  header: 'المنفِّذ',
                  cell: (e) => (
                    <span className="font-body text-body text-on-surface">
                      {e.actor_name ?? (e.actor_user_id ? <Mono>#{e.actor_user_id}</Mono> : '—')}
                    </span>
                  ),
                },
                {
                  header: 'الهدف',
                  cell: (e) =>
                    e.target_name ? (
                      <span className="font-body text-body text-on-surface">{e.target_name}</span>
                    ) : e.target_type || e.target_id ? (
                      <span className="font-body text-body text-secondary">
                        {e.target_type ? `${e.target_type} ` : ''}
                        {e.target_id ? <Mono>#{e.target_id}</Mono> : ''}
                      </span>
                    ) : (
                      '—'
                    ),
                },
                { header: 'عنوان IP', cell: (e) => <span dir="ltr"><Mono>{e.ip ?? '—'}</Mono></span> },
                {
                  header: 'نظام التشغيل',
                  cell: (e) => (
                    <span className="font-body text-body text-secondary" title={e.user_agent ?? undefined}>
                      {e.os ?? '—'}
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

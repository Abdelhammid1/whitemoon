import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Spinner, EmptyState } from '../../components/ui'
import { listOrPending, EndpointPending } from '../../api/pending'

interface AuditRow {
  id: number
  at: string
  actor_user_id: number | null
  action: string
  target_type: string | null
  target_id: string | null
}

export function AuditLogPage() {
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState(false)
  const [rows, setRows] = useState<AuditRow[]>([])

  useEffect(() => {
    listOrPending<AuditRow>('/admin/audit')
      .then(setRows)
      .catch((err) => {
        if (err instanceof EndpointPending) setPending(true)
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <Wide>
      <PageTitle title="سجل التدقيق" subtitle="كل عملية حساسة في المنظومة موثّقة بالمنفِّذ والهدف والوقت." />
      <div className="mt-space-xl">
        {loading ? (
          <Spinner />
        ) : pending || rows.length === 0 ? (
          <EmptyState
            title="واجهة قراءة سجل التدقيق قيد الإنشاء"
            description="الأحداث تُكتب فعليًا في قاعدة البيانات (audit.events)؛ واجهة العرض لم تُفعَّل بعد على الخادم."
          />
        ) : null}
      </div>
    </Wide>
  )
}

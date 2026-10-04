import { useEffect, useState, type ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, SectionHeader, EmptyState, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { getUser, listAudit, type UserDetail, type AuditRow } from '../../api/admin'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

const KIND_AR: Record<string, string> = {
  customer: 'عميل', supplier: 'مورد', agent: 'وكيل', branch: 'فرع', staff: 'موظف', admin: 'مدير',
}
const STATUS_TONE: Record<string, 'signal' | 'warning' | 'error' | 'neutral'> = {
  active: 'signal', pending: 'warning', suspended: 'error', locked: 'error',
}

export function UserDetailPage() {
  const { id } = useParams()
  const uid = Number(id)
  const [user, setUser] = useState<UserDetail | null>(null)
  const [activity, setActivity] = useState<AuditRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.all([getUser(uid), listAudit({ limit: 300 })])
      .then(([u, audit]) => {
        if (!active) return
        setUser(u)
        setActivity(
          audit.items.filter((e) => e.actor_user_id === uid || e.target_id === String(uid)),
        )
      })
      .catch((err) => active && setError(err instanceof ApiError ? err.message : 'تعذّر التحميل'))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [uid])

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error || !user) {
    return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>
  }

  const Row = ({ label, value }: { label: string; value: ReactNode }) => (
    <div className="flex items-center justify-between py-space-sm border-b border-surface-container-high">
      <span className="font-small text-small text-secondary">{label}</span>
      <span className="font-body text-body text-on-surface">{value}</span>
    </div>
  )

  return (
    <Narrow>
      <div className="flex items-center gap-space-md">
        <PageTitle title={user.email ?? user.phone ?? `#${user.id}`} />
      </div>
      <div className="mt-space-sm flex flex-wrap items-center gap-space-sm">
        <Pill tone="neutral">{KIND_AR[user.kind] ?? user.kind}</Pill>
        <Pill tone={STATUS_TONE[user.status] ?? 'neutral'}>{user.status}</Pill>
        {user.roles.map((r) => <Pill key={r} tone="neutral">{r}</Pill>)}
      </div>

      <section className="mt-[48px]">
        <div className="flex flex-col">
          <Row label="المعرف" value={<Mono>{user.id}</Mono>} />
          <Row label="الهاتف" value={<Mono>{user.phone ?? '—'}</Mono>} />
          <Row label="البريد" value={<Mono>{user.email ?? '—'}</Mono>} />
          <Row label="النوع" value={KIND_AR[user.kind] ?? user.kind} />
          <Row label="تاريخ الإنشاء" value={<Mono>{formatDate(user.created_at)}</Mono>} />
          <Row label="تاريخ التفعيل" value={<Mono>{user.activated_at ? formatDate(user.activated_at) : '—'}</Mono>} />
        </div>
      </section>

      <section className="mt-[48px]">
        <SectionHeader title="النشاط الأخير" />
        {activity.length === 0 ? (
          <EmptyState title="لا يوجد نشاط مسجّل لهذا المستخدم." />
        ) : (
          <DataTable
            rows={activity}
            rowKey={(e) => e.id}
            columns={[
              { header: 'الوقت', cell: (e) => <Mono>{formatDate(e.at)}</Mono> },
              { header: 'الإجراء', cell: (e) => <Pill tone="neutral">{e.action}</Pill> },
              { header: 'الهدف', cell: (e) => <span className="font-body text-body text-secondary">{e.target_type ?? '—'} {e.target_id ? `#${e.target_id}` : ''}</span> },
            ]}
          />
        )}
      </section>
    </Narrow>
  )
}

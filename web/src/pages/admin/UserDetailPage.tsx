import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, SectionHeader, EmptyState } from '../../components/ui'
import { Mono } from '../../components/DataTable'
import { listUsers, type AdminUser } from '../../api/admin'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

const KIND_AR: Record<string, string> = {
  customer: 'عميل', supplier: 'مورد', agent: 'وكيل', branch: 'فرع', staff: 'موظف', admin: 'مدير',
}

export function UserDetailPage() {
  const { id } = useParams()
  const [user, setUser] = useState<AdminUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const uid = Number(id)
    listUsers({ limit: 200 })
      .then((r) => {
        const found = r.items.find((u) => u.id === uid) ?? null
        setUser(found)
        if (!found) setError('المستخدم غير موجود في القائمة.')
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'تعذّر التحميل'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error || !user) return <Narrow><p className="font-body text-body text-[#B3261E] mt-space-xl">{error ?? 'غير موجود'}</p></Narrow>

  const Row = ({ label, value }: { label: string; value: React.ReactNode }) => (
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
      <div className="mt-space-sm flex items-center gap-space-sm">
        <Pill tone="neutral">{KIND_AR[user.kind] ?? user.kind}</Pill>
        <Pill tone={user.status === 'active' ? 'signal' : user.status === 'pending' ? 'warning' : 'error'}>
          {user.status}
        </Pill>
      </div>

      <section className="mt-[48px]">
        <div className="flex flex-col">
          <Row label="المعرف" value={<Mono>{user.id}</Mono>} />
          <Row label="الهاتف" value={<Mono>{user.phone ?? '—'}</Mono>} />
          <Row label="البريد" value={<Mono>{user.email ?? '—'}</Mono>} />
          <Row label="النوع" value={KIND_AR[user.kind] ?? user.kind} />
          <Row label="تاريخ الإنشاء" value={<Mono>{formatDate(user.created_at)}</Mono>} />
        </div>
      </section>

      <section className="mt-[48px]">
        <SectionHeader title="النشاط الأخير" />
        <EmptyState
          title="سجل نشاط المستخدم غير متاح بعد"
          description="واجهة قراءة سجل التدقيق قيد الإنشاء على الخادم."
        />
      </section>
    </Narrow>
  )
}

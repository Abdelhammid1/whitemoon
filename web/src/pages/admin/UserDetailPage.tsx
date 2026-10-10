import { useEffect, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Pill, Button, Field, Spinner, SectionHeader, EmptyState, InlineError, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { PageHelp } from '../../components/PageHelp'
import {
  getUser, listAudit, updateUserProfile, getUserPermissions, grantUserPermission,
  revokeUserPermission, type UserDetail, type AuditRow, type UserPermissions,
} from '../../api/admin'
import { ApiError } from '../../api/client'
import { useToast } from '../../components/Toast'
import { formatDate } from '../../lib/format'
import { USER_STATUS_AR, label } from '../../lib/labels'

const KIND_AR: Record<string, string> = {
  customer: 'عميل', supplier: 'مورد', agent: 'وكيل', branch: 'فرع', staff: 'موظف', admin: 'مدير',
}
const STATUS_TONE: Record<string, 'signal' | 'warning' | 'error' | 'neutral'> = {
  active: 'signal', pending: 'warning', suspended: 'error', locked: 'error',
}

export function UserDetailPage() {
  const { id } = useParams()
  const uid = Number(id)
  const toast = useToast()
  const [user, setUser] = useState<UserDetail | null>(null)
  const [activity, setActivity] = useState<AuditRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [geoArea, setGeoArea] = useState('')
  const [minOrder, setMinOrder] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    getUser(uid)
      .then((u) => {
        if (!active) return
        setUser(u)
        setGeoArea(u.geo_area ?? '')
        setMinOrder(u.min_order_value ?? '')
        // Activity needs the governance (admin.high) audit read; best-effort
        // so a non-senior viewer still sees the user detail without it.
        return listAudit({ limit: 300 })
          .then((audit) => {
            if (!active) return
            setActivity(
              audit.items.filter((e) => e.actor_user_id === uid || e.target_id === String(uid)),
            )
          })
          .catch(() => { /* no audit access — leave activity empty */ })
      })
      .catch((err) => active && setError(err instanceof ApiError ? err.message : 'تعذّر التحميل'))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [uid])

  async function refresh() {
    const u = await getUser(uid)
    setUser(u)
    setGeoArea(u.geo_area ?? '')
    setMinOrder(u.min_order_value ?? '')
  }

  async function saveProfile(body: { geo_area?: string; min_order_value?: number }) {
    setBusy(true)
    try {
      await updateUserProfile(uid, body)
      toast.success('تم الحفظ.')
      await refresh()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر الحفظ')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error || !user) {
    return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>
  }

  const Row = ({ label, value }: { label: string; value: ReactNode }) => (
    <div className="flex items-center justify-between py-space-sm border-b border-surface-container-high last:border-b-0">
      <span className="font-small text-small text-secondary">{label}</span>
      <span className="font-body text-body text-on-surface">{value}</span>
    </div>
  )

  return (
    <Narrow>
      <div className="flex flex-wrap items-center justify-between gap-space-md">
        <PageTitle title={user.email ?? user.phone ?? `#${user.id}`} />
        {user.kind === 'customer' && (
          <Link to={`/admin/customers/${user.id}/statement`}>
            <Button iconRight="account_balance_wallet">كشف الحساب</Button>
          </Link>
        )}
      </div>
      <div className="mt-space-sm flex flex-wrap items-center gap-space-sm">
        <Pill tone="neutral">{KIND_AR[user.kind] ?? user.kind}</Pill>
        <Pill tone={STATUS_TONE[user.status] ?? 'neutral'}>{label(USER_STATUS_AR, user.status)}</Pill>
        {user.roles.map((r) => <Pill key={r} tone="brand">{r}</Pill>)}
      </div>

      <PageHelp pageKey="user-detail" />

      <section className="mt-space-xl">
        <Card>
          <div className="flex flex-col">
            <Row label="المعرف" value={<Mono>{user.id}</Mono>} />
            <Row label="الهاتف" value={<Mono>{user.phone ?? '—'}</Mono>} />
            <Row label="البريد" value={<Mono>{user.email ?? '—'}</Mono>} />
            <Row label="النوع" value={KIND_AR[user.kind] ?? user.kind} />
            <Row label="تاريخ الإنشاء" value={<Mono>{formatDate(user.created_at)}</Mono>} />
            <Row label="تاريخ التفعيل" value={<Mono>{user.activated_at ? formatDate(user.activated_at) : '—'}</Mono>} />
          </div>
        </Card>
      </section>

      {user.kind === 'customer' && (
        <section className="mt-space-xl">
          <Card>
            <SectionHeader title="النطاق الجغرافي" />
            <div className="mt-space-md flex items-end gap-space-sm">
              <div className="flex-1">
                <Field label="المنطقة الجغرافية" value={geoArea} onChange={(e) => setGeoArea(e.target.value)} />
              </div>
              <Button variant="primary" disabled={busy} onClick={() => void saveProfile({ geo_area: geoArea })}>حفظ</Button>
            </div>
            <p className="mt-space-xs font-small text-small text-secondary">
              تحدِّد أي وكيل يمكنه خدمة هذا العميل (نطاق التغطية). بدونها يُرفض وصول الوكيل.
            </p>
          </Card>
        </section>
      )}

      {user.kind === 'supplier' && (
        <section className="mt-space-xl">
          <Card>
            <SectionHeader title="شروط المورد" />
            <div className="mt-space-md flex items-end gap-space-sm">
              <div className="w-56">
                <Field label="الحد الأدنى للطلب (ج.م)" dir="ltr" mono inputMode="decimal" value={minOrder} onChange={(e) => setMinOrder(e.target.value)} />
              </div>
              <Button variant="primary" disabled={busy || minOrder === ''} onClick={() => void saveProfile({ min_order_value: Number(minOrder) })}>حفظ</Button>
            </div>
            <p className="mt-space-xs font-small text-small text-secondary">
              أقل قيمة مسموح بها لطلب يحتوي على أصناف هذا المورد.
            </p>
          </Card>
        </section>
      )}

      {['staff', 'admin', 'agent', 'branch'].includes(user.kind) && (
        <section className="mt-space-xl">
          <PermissionsSection userId={uid} />
        </section>
      )}

      <section className="mt-space-xl">
        <SectionHeader title="النشاط الأخير" />
        {activity.length === 0 ? (
          <Card className="mt-space-md"><EmptyState title="لا يوجد نشاط مسجّل لهذا المستخدم." /></Card>
        ) : (
          <Card padded={false} className="mt-space-md overflow-hidden">
            <DataTable
              rows={activity}
              rowKey={(e) => e.id}
              columns={[
                { header: 'الوقت', cell: (e) => <Mono>{formatDate(e.at)}</Mono> },
                { header: 'الإجراء', cell: (e) => <Pill tone="neutral">{e.action}</Pill> },
                { header: 'الهدف', cell: (e) => <span className="font-body text-body text-secondary">{e.target_type ?? '—'} {e.target_id ? `#${e.target_id}` : ''}</span> },
              ]}
            />
          </Card>
        )}
      </section>
    </Narrow>
  )
}

function PermissionsSection({ userId }: { userId: number }) {
  const toast = useToast()
  const [data, setData] = useState<UserPermissions | null>(null)
  const [busy, setBusy] = useState('')

  async function load() {
    try {
      setData(await getUserPermissions(userId))
    } catch {
      /* non-senior viewer — leave empty */
    }
  }
  useEffect(() => { void load() }, [userId])

  async function toggle(code: string, on: boolean) {
    setBusy(code)
    try {
      if (on) await grantUserPermission(userId, code)
      else await revokeUserPermission(userId, code)
      toast.success('تم تحديث الصلاحيات.')
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر التحديث')
    } finally {
      setBusy('')
    }
  }

  if (!data) return null
  return (
    <>
      <SectionHeader title="صلاحيات مخصّصة" />
      <Card className="mt-space-md flex flex-col gap-space-sm">
        <p className="font-small text-small text-secondary">
          امنح هذا المستخدم صلاحيات إضافية فوق دوره. يُسجَّل كل تغيير في التدقيق.
        </p>
        {data.delegatable.map((p) => {
          const has = data.direct.includes(p.code)
          return (
            <div key={p.code} className="flex items-center justify-between gap-space-md border-t border-surface-container-high pt-space-sm first:border-0 first:pt-0">
              <span className="font-body text-body text-on-surface">{p.label}</span>
              <Button
                variant={has ? 'destructive' : 'primary'}
                disabled={busy === p.code}
                onClick={() => void toggle(p.code, !has)}
              >
                {has ? 'إلغاء' : 'منح'}
              </Button>
            </div>
          )
        })}
      </Card>
    </>
  )
}

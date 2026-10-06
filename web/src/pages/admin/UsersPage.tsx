import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Field, Button, Spinner, Card, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import { createUser, listUsers, listRoles, listUserKinds, listUserStatuses, type AdminUser, type Role, type CodeLabel } from '../../api/admin'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

const KIND_AR: Record<string, string> = {
  '': 'الكل', customer: 'عميل', supplier: 'مورد', agent: 'وكيل',
  branch: 'فرع', staff: 'موظف', admin: 'مدير',
}
const STATUS_AR: Record<string, string> = {
  '': 'الكل', pending: 'قيد الاعتماد', active: 'مفعّل', suspended: 'مجمّد', locked: 'مغلق',
}
const STATUS_TONE: Record<string, 'signal' | 'warning' | 'error' | 'neutral'> = {
  active: 'signal', pending: 'warning', suspended: 'error', locked: 'error',
}

// Graceful fallbacks used only until the backend enum lists load (or if they fail).
const FALLBACK_KINDS: CodeLabel[] = [
  { code: 'customer', label: 'عميل' }, { code: 'supplier', label: 'مورد' },
  { code: 'agent', label: 'وكيل' }, { code: 'branch', label: 'فرع' },
  { code: 'staff', label: 'موظف' }, { code: 'admin', label: 'مدير' },
]
const FALLBACK_STATUSES: CodeLabel[] = [
  { code: 'pending', label: 'قيد الاعتماد' }, { code: 'active', label: 'مفعّل' },
  { code: 'suspended', label: 'مجمّد' }, { code: 'locked', label: 'مغلق' },
]
// Fallback role list used only if the backend role registry can't be reached.
const FALLBACK_ROLES: Role[] = [
  { code: 'customer', name_ar: 'عميل', name_en: 'Customer' },
  { code: 'supplier', name_ar: 'مورد', name_en: 'Supplier' },
  { code: 'agent', name_ar: 'وكيل', name_en: 'Agent' },
  { code: 'branch', name_ar: 'فرع', name_en: 'Branch' },
  { code: 'staff', name_ar: 'موظف', name_en: 'Staff' },
  { code: 'admin', name_ar: 'مدير', name_en: 'Admin' },
  { code: 'admin.high', name_ar: 'مدير أعلى', name_en: 'Super Admin' },
]

const emptyForm = {
  kind: 'customer', roles: ['customer'] as string[], display_name: '',
  phone: '', email: '', password: '', status: 'active', geo_area: '',
}

export function UsersPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const [q, setQ] = useState('')
  const [kind, setKind] = useState('')
  const [status, setStatus] = useState('')
  const [rows, setRows] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [roles, setRoles] = useState<Role[]>(FALLBACK_ROLES)
  const [kinds, setKinds] = useState<CodeLabel[]>(FALLBACK_KINDS)
  const [statuses, setStatuses] = useState<CodeLabel[]>(FALLBACK_STATUSES)

  // Role registry and enum lists (kinds/statuses) are loaded from the backend —
  // nothing hard-coded; each falls back to its seed only if the request fails.
  useEffect(() => {
    let alive = true
    void (async () => {
      try {
        const resp = await listRoles()
        if (alive && resp.items.length) setRoles(resp.items)
      } catch {
        /* keep FALLBACK_ROLES */
      }
    })()
    void (async () => {
      try {
        const resp = await listUserKinds()
        if (alive && resp.items.length) setKinds(resp.items)
      } catch {
        /* keep FALLBACK_KINDS */
      }
    })()
    void (async () => {
      try {
        const resp = await listUserStatuses()
        if (alive && resp.items.length) setStatuses(resp.items)
      } catch {
        /* keep FALLBACK_STATUSES */
      }
    })()
    return () => { alive = false }
  }, [])

  // Picking a kind preselects the matching role.
  function setFormKind(k: string) {
    // Reset roles to the one matching the chosen kind; the admin can add more.
    setForm((f) => ({ ...f, kind: k, roles: [k] }))
  }
  function toggleRole(code: string) {
    setForm((f) => ({
      ...f,
      roles: f.roles.includes(code) ? f.roles.filter((r) => r !== code) : [...f.roles, code],
    }))
  }

  const canSubmit =
    !busy && form.display_name.trim().length > 0 && form.password.length >= 8 &&
    (form.phone.trim() !== '' || form.email.trim() !== '') && form.roles.length > 0

  async function submitNew() {
    setBusy(true)
    try {
      await createUser({
        kind: form.kind,
        roles: form.roles,
        display_name: form.display_name.trim(),
        password: form.password,
        status: form.status,
        phone: form.phone.trim() || undefined,
        email: form.email.trim() || undefined,
        geo_area: form.kind === 'customer' && form.geo_area.trim() ? form.geo_area.trim() : undefined,
      })
      toast.success('تم إنشاء المستخدم.')
      setOpen(false)
      setForm(emptyForm)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر إنشاء المستخدم')
    } finally {
      setBusy(false)
    }
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const resp = await listUsers({ q: q || undefined, kind: kind || undefined, status: status || undefined, limit: 100 })
      setRows(resp.items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [kind, status]) // eslint-disable-line react-hooks/exhaustive-deps

  const chip = (active: boolean) =>
    `px-2 py-0.5 rounded-full font-small text-small transition-colors ${
      active ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant hover:text-primary'
    }`

  return (
    <Wide>
      <div className="flex items-start justify-between gap-space-md">
        <PageTitle title="المستخدمون" subtitle="بحث وفلترة حسابات المنظومة." />
        <Button variant="primary" onClick={() => setOpen(true)}>إضافة مستخدم</Button>
      </div>

      <PageHelp pageKey="users" />

      <Card className="mt-space-xl flex flex-col gap-space-md">
        <form onSubmit={(e) => { e.preventDefault(); void load() }} className="max-w-[420px]">
          <Field label="بحث (هاتف/بريد)" dir="ltr" value={q} onChange={(e) => setQ(e.target.value)} />
        </form>
        <div className="flex flex-col gap-space-sm">
          <span className="font-small text-small text-secondary">النوع</span>
          <div className="flex flex-wrap gap-space-xs">
            <button key="any" className={chip(kind === '')} onClick={() => setKind('')}>{KIND_AR['']}</button>
            {kinds.map((k) => (
              <button key={k.code} className={chip(kind === k.code)} onClick={() => setKind(k.code)}>{k.label}</button>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-space-sm">
          <span className="font-small text-small text-secondary">الحالة</span>
          <div className="flex flex-wrap gap-space-xs">
            <button key="any" className={chip(status === '')} onClick={() => setStatus('')}>{STATUS_AR['']}</button>
            {statuses.map((s) => (
              <button key={s.code} className={chip(status === s.code)} onClick={() => setStatus(s.code)}>{s.label}</button>
            ))}
          </div>
        </div>
      </Card>

      <div className="mt-space-lg">
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : (
          <Card padded={false} className="overflow-hidden">
            <DataTable
              rows={rows}
              rowKey={(u) => u.id}
              onRowClick={(u) => navigate(`/admin/users/${u.id}`)}
              empty="لا يوجد مستخدمون مطابقون."
              columns={[
                { header: 'المعرف', width: '70px', cell: (u) => <Mono>{u.id}</Mono> },
                { header: 'الهاتف', cell: (u) => <Mono>{u.phone ?? '—'}</Mono> },
                { header: 'البريد', cell: (u) => <Mono>{u.email ?? '—'}</Mono> },
                { header: 'النوع', cell: (u) => <Pill tone="neutral">{KIND_AR[u.kind] ?? u.kind}</Pill> },
                { header: 'الحالة', cell: (u) => <Pill tone={STATUS_TONE[u.status] ?? 'neutral'}>{STATUS_AR[u.status] ?? u.status}</Pill> },
                { header: 'تاريخ الإنشاء', align: 'end', cell: (u) => <Mono>{formatDate(u.created_at)}</Mono> },
              ]}
            />
          </Card>
        )}
      </div>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="إضافة مستخدم"
        footer={
          <>
            <Button onClick={() => setOpen(false)}>إلغاء</Button>
            <Button variant="primary" disabled={!canSubmit} onClick={() => void submitNew()}>
              إنشاء
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-space-md">
          <div className="flex flex-col gap-space-sm">
            <p className="font-small-medium text-small-medium text-secondary">النوع</p>
            <div className="flex flex-wrap gap-space-xs">
              {kinds.map((k) => (
                <button key={k.code} type="button" className={chip(form.kind === k.code)} onClick={() => setFormKind(k.code)}>
                  {k.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-space-sm">
            <p className="font-small-medium text-small-medium text-secondary">الأدوار</p>
            <div className="flex flex-wrap gap-space-md">
              {roles.map((r) => (
                <label key={r.code} className="flex items-center gap-space-xs font-body text-body">
                  <input type="checkbox" checked={form.roles.includes(r.code)} onChange={() => toggleRole(r.code)} />
                  {r.name_ar}
                </label>
              ))}
            </div>
          </div>

          <Field label="الاسم" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            <Field label="الهاتف (اختياري)" dir="ltr" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            <Field label="البريد (اختياري)" dir="ltr" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <Field label="كلمة المرور (٨ أحرف فأكثر)" type="password" dir="ltr" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          {form.kind === 'customer' && (
            <Field label="المنطقة الجغرافية (اختياري)" value={form.geo_area} onChange={(e) => setForm({ ...form, geo_area: e.target.value })} hint="تُستخدم لتحديد نطاق الوكيل." />
          )}

          <div className="flex flex-col gap-space-sm">
            <p className="font-small-medium text-small-medium text-secondary">الحالة</p>
            <div className="flex gap-space-xs">
              {statuses.map((s) => (
                <button key={s.code} type="button" className={chip(form.status === s.code)} onClick={() => setForm({ ...form, status: s.code })}>
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {form.phone.trim() === '' && form.email.trim() === '' && (
            <InlineError message="مطلوب هاتف أو بريد على الأقل." />
          )}
        </div>
      </Modal>
    </Wide>
  )
}

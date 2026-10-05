import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Field, Button, Spinner } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { createUser, listUsers, type AdminUser } from '../../api/admin'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

const KINDS = ['', 'customer', 'supplier', 'agent', 'branch', 'staff', 'admin']
const STATUSES = ['', 'pending', 'active', 'suspended', 'locked']

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

// Create-user form options.
const NEW_KINDS = ['customer', 'supplier', 'agent', 'branch', 'staff', 'admin'] as const
const ROLE_OPTIONS = ['customer', 'supplier', 'agent', 'branch', 'staff', 'admin', 'admin.high']
const ROLE_AR: Record<string, string> = { ...KIND_AR, 'admin.high': 'مدير أعلى' }
const NEW_STATUSES = ['active', 'pending', 'suspended'] as const

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

  // Picking a kind preselects the matching role.
  function setFormKind(k: string) {
    setForm((f) => ({ ...f, kind: k, roles: f.roles.length ? f.roles : [k] }))
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
    `px-2 py-0.5 rounded-full font-mono-body text-small transition-colors ${
      active ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant hover:text-primary'
    }`

  return (
    <Wide>
      <div className="flex items-start justify-between gap-space-md">
        <PageTitle title="المستخدمون" subtitle="بحث وفلترة حسابات المنظومة." />
        <Button variant="primary" onClick={() => setOpen(true)}>إضافة مستخدم</Button>
      </div>

      <div className="mt-space-xl flex flex-col gap-space-md">
        <form onSubmit={(e) => { e.preventDefault(); void load() }} className="max-w-[420px]">
          <Field label="بحث (هاتف/بريد)" dir="ltr" value={q} onChange={(e) => setQ(e.target.value)} />
        </form>
        <div className="flex flex-wrap items-center gap-space-md">
          <div className="flex flex-wrap gap-space-xs">
            {KINDS.map((k) => (
              <button key={k || 'any'} className={chip(kind === k)} onClick={() => setKind(k)}>{KIND_AR[k]}</button>
            ))}
          </div>
          <div className="flex flex-wrap gap-space-xs">
            {STATUSES.map((s) => (
              <button key={s || 'any'} className={chip(status === s)} onClick={() => setStatus(s)}>{STATUS_AR[s]}</button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-space-lg">
        {loading ? (
          <Spinner />
        ) : error ? (
          <p className="font-body text-body text-[#B3261E] py-space-md">{error}</p>
        ) : (
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
          <div>
            <span className="font-small text-small text-secondary mb-1 block">النوع</span>
            <div className="flex flex-wrap gap-space-xs">
              {NEW_KINDS.map((k) => (
                <button key={k} type="button" className={chip(form.kind === k)} onClick={() => setFormKind(k)}>
                  {KIND_AR[k]}
                </button>
              ))}
            </div>
          </div>

          <div>
            <span className="font-small text-small text-secondary mb-1 block">الأدوار</span>
            <div className="flex flex-wrap gap-space-md">
              {ROLE_OPTIONS.map((code) => (
                <label key={code} className="flex items-center gap-space-xs font-body text-body">
                  <input type="checkbox" checked={form.roles.includes(code)} onChange={() => toggleRole(code)} />
                  {ROLE_AR[code] ?? code}
                </label>
              ))}
            </div>
          </div>

          <Field label="الاسم" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
          <div className="flex gap-space-md">
            <div className="flex-1"><Field label="الهاتف (اختياري)" dir="ltr" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
            <div className="flex-1"><Field label="البريد (اختياري)" dir="ltr" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
          </div>
          <Field label="كلمة المرور (٨ أحرف فأكثر)" type="password" dir="ltr" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          {form.kind === 'customer' && (
            <Field label="المنطقة الجغرافية (اختياري)" value={form.geo_area} onChange={(e) => setForm({ ...form, geo_area: e.target.value })} hint="تُستخدم لتحديد نطاق الوكيل." />
          )}

          <div>
            <span className="font-small text-small text-secondary mb-1 block">الحالة</span>
            <div className="flex gap-space-xs">
              {NEW_STATUSES.map((s) => (
                <button key={s} type="button" className={chip(form.status === s)} onClick={() => setForm({ ...form, status: s })}>
                  {STATUS_AR[s]}
                </button>
              ))}
            </div>
          </div>

          {form.phone.trim() === '' && form.email.trim() === '' && (
            <span className="font-small text-small text-[#B3261E]">مطلوب هاتف أو بريد على الأقل.</span>
          )}
        </div>
      </Modal>
    </Wide>
  )
}

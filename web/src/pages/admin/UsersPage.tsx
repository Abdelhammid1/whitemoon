import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Field, Spinner } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { listUsers, type AdminUser } from '../../api/admin'
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

export function UsersPage() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [kind, setKind] = useState('')
  const [status, setStatus] = useState('')
  const [rows, setRows] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
      <PageTitle title="المستخدمون" subtitle="بحث وفلترة حسابات المنظومة." />

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
    </Wide>
  )
}

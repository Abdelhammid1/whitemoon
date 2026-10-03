import { useEffect, useState } from 'react'
import { Card, CardHeader } from '../../components/Card'
import { Input } from '../../components/Input'
import { Button } from '../../components/Button'
import { Chip } from '../../components/Chip'
import { Badge } from '../../components/Badge'
import { Table } from '../../components/Table'
import { listUsers, type AdminUser } from '../../api/admin'
import { ApiError } from '../../api/client'
import { useToast } from '../../components/Toast'
import { formatDate } from '../../lib/format'

const KINDS = ['', 'customer', 'supplier', 'agent', 'branch', 'staff', 'admin'] as const

export function UsersPage() {
  const toast = useToast()
  const [q, setQ] = useState<string>('')
  const [kind, setKind] = useState<string>('')
  const [status, setStatus] = useState<string>('')
  const [rows, setRows] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState<boolean>(true)

  async function load() {
    setLoading(true)
    try {
      const resp = await listUsers({
        q: q || undefined,
        kind: kind || undefined,
        status: status || undefined,
        limit: 100,
      })
      setRows(resp.items)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر تحميل المستخدمين')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader title="المستخدمون" subtitle="بحث وفلترة" />
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[220px] flex-1">
            <Input
              label="بحث (هاتف/بريد)"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              dir="ltr"
            />
          </div>
          <div className="min-w-[180px]">
            <label className="text-body-sm text-graphite">النوع</label>
            <div className="mt-1 flex flex-wrap gap-1">
              {KINDS.map((k) => (
                <Chip key={k || 'any'} active={kind === k} onClick={() => setKind(k)}>
                  {kindLabel(k)}
                </Chip>
              ))}
            </div>
          </div>
          <div className="min-w-[180px]">
            <label className="text-body-sm text-graphite">الحالة</label>
            <div className="mt-1 flex flex-wrap gap-1">
              {['', 'pending', 'active', 'suspended', 'locked'].map((s) => (
                <Chip key={s || 'any'} active={status === s} onClick={() => setStatus(s)}>
                  {statusLabel(s)}
                </Chip>
              ))}
            </div>
          </div>
          <Button variant="filled" onClick={load} disabled={loading}>
            {loading ? 'جار البحث…' : 'بحث'}
          </Button>
        </div>
      </Card>

      <Card>
        <Table
          rowKey={(u) => u.id}
          rows={rows}
          columns={[
            { header: 'المعرّف', cell: (u) => <span className="font-mono text-ink">{u.id}</span>, width: '80px' },
            { header: 'الهاتف', cell: (u) => <span dir="ltr">{u.phone ?? '—'}</span> },
            { header: 'البريد', cell: (u) => <span dir="ltr">{u.email ?? '—'}</span> },
            {
              header: 'النوع',
              cell: (u) => <Badge tone="neutral">{kindLabel(u.kind)}</Badge>,
            },
            {
              header: 'الحالة',
              cell: (u) => <Badge tone="muted">{statusLabel(u.status)}</Badge>,
            },
            { header: 'تاريخ الإنشاء', cell: (u) => formatDate(u.created_at) },
          ]}
        />
      </Card>
    </div>
  )
}

function kindLabel(k: string): string {
  if (!k) return 'الكل'
  return (
    (
      {
        customer: 'عميل',
        supplier: 'مورد',
        agent: 'وكيل',
        branch: 'فرع',
        staff: 'موظف',
        admin: 'مدير',
      } as Record<string, string>
    )[k] ?? k
  )
}

function statusLabel(s: string): string {
  if (!s) return 'الكل'
  return (
    (
      {
        pending: 'قيد الاعتماد',
        active: 'مفعّل',
        suspended: 'مجمّد',
        locked: 'مغلق',
      } as Record<string, string>
    )[s] ?? s
  )
}

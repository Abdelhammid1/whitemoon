import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, InlineError, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { createPartner, listPartners, type Partner } from '../../api/partners'
import { ApiError } from '../../api/client'

export function PartnersPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [rows, setRows] = useState<Partner[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ type: 'agent', display_name: '', geo_scope: '', email: '', password: '' })

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setRows((await listPartners()).items) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  async function create() {
    setBusy(true)
    try {
      await createPartner({ ...form })
      toast.success('أُنشئ الشريك.')
      setOpen(false); setForm({ type: 'agent', display_name: '', geo_scope: '', email: '', password: '' })
      await load()
    } catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر الإنشاء') }
    finally { setBusy(false) }
  }

  const f = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm((s) => ({ ...s, [k]: e.target.value }))

  return (
    <Wide>
      <div className="flex items-center justify-between gap-space-md">
        <PageTitle title="الوكلاء والفروع" subtitle="إدارة شركاء القناة: الشروط، التأمينات، الاستحقاقات." />
        <Button variant="primary" onClick={() => setOpen(true)}>شريك جديد</Button>
      </div>
      <div className="mt-space-xl">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : (
          <Card padded={false} className="overflow-hidden">
            <DataTable rows={rows} rowKey={(p) => p.partner_id} onRowClick={(p) => navigate(`/partners/${p.partner_id}`)}
              empty="لا يوجد شركاء." columns={[
                { header: 'المعرف', width: '70px', cell: (p) => <Mono>{p.partner_id}</Mono> },
                { header: 'الاسم', cell: (p) => <span className="font-body-medium text-body-medium text-on-surface">{p.display_name}</span> },
                { header: 'النوع', align: 'center', cell: (p) => <Pill tone={p.type === 'agent' ? 'brand' : 'neutral'}>{p.type === 'agent' ? 'وكيل' : 'فرع'}</Pill> },
                { header: 'النطاق', cell: (p) => p.geo_scope ?? '—' },
              ]} />
          </Card>
        )}
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="شريك جديد (وكيل / فرع)"
        footer={<><Button onClick={() => setOpen(false)}>إلغاء</Button>
          <Button variant="primary" disabled={busy || !form.display_name || !form.password} onClick={create}>إنشاء</Button></>}>
        <div className="flex flex-col gap-space-md">
          <div className="flex flex-col gap-space-sm">
            <p className="font-small-medium text-small-medium text-secondary">النوع</p>
            <div className="flex gap-space-sm">
              {(['agent', 'branch'] as const).map((t) => (
                <button key={t} onClick={() => setForm((s) => ({ ...s, type: t }))}
                  className={`px-3 py-1 rounded-full font-small ${form.type === t ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant'}`}>
                  {t === 'agent' ? 'وكيل' : 'فرع'}
                </button>
              ))}
            </div>
          </div>
          <Field label="الاسم الظاهر" value={form.display_name} onChange={f('display_name')} />
          <Field label="النطاق الجغرافي" value={form.geo_scope} onChange={f('geo_scope')} />
          <Field label="البريد" dir="ltr" value={form.email} onChange={f('email')} />
          <Field label="كلمة المرور" type="password" dir="ltr" value={form.password} onChange={f('password')} />
        </div>
      </Modal>
    </Wide>
  )
}

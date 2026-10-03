import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { SideSheet } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { listShortages, resolveShortage, type Shortage } from '../../api/inventory'
import { ApiError } from '../../api/client'

const STATUS: Record<string, { ar: string; tone: 'signal' | 'warning' | 'error' }> = {
  pending: { ar: 'قيد الحسم', tone: 'warning' },
  resolved: { ar: 'محسوم', tone: 'signal' },
  rejected: { ar: 'مرفوض', tone: 'error' },
}

export function ShortagesPage() {
  const toast = useToast()
  const [rows, setRows] = useState<Shortage[]>([])
  const [loading, setLoading] = useState(true)
  const [active, setActive] = useState<Shortage | null>(null)
  const [party, setParty] = useState('supplier')
  const [partyId, setPartyId] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    try { setRows((await listShortages({})).items) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function onResolve() {
    if (!active) return
    setBusy(true)
    try {
      await resolveShortage(active.id, {
        responsible_party_type: party,
        responsible_party_id: party === 'channel_partner' ? Number(partyId) : undefined,
        reason,
      })
      toast.success('تم الحسم وترحيل القيد.')
      setActive(null); setReason(''); setPartyId(''); setParty('supplier')
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الحسم')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Wide>
      <PageTitle title="النواقص والمرتجعات" subtitle="تُحسم القيمة من الطرف المسؤول، ويُرحَّل القيد تلقائيًا." />

      <div className="mt-space-xl">
        {loading ? <Spinner /> : (
          <DataTable rows={rows} rowKey={(s) => s.id} onRowClick={(s) => s.status === 'pending' && setActive(s)} empty="لا توجد بلاغات نواقص." columns={[
            { header: 'المعرف', width: '70px', cell: (s) => <Mono>{s.id}</Mono> },
            { header: 'المنتج', cell: (s) => <Mono>{s.product_id}</Mono> },
            { header: 'المورد', cell: (s) => <Mono>{s.supplier_id}</Mono> },
            { header: 'الكمية', align: 'end', cell: (s) => <Mono>{s.qty}</Mono> },
            { header: 'التكلفة', align: 'end', cell: (s) => <Mono>{s.unit_cost}</Mono> },
            { header: 'القيد', align: 'end', cell: (s) => (s.journal_entry_id ? <Mono>JV #{s.journal_entry_id}</Mono> : '—') },
            { header: 'الحالة', align: 'end', cell: (s) => <Pill tone={STATUS[s.status]?.tone ?? 'warning'}>{STATUS[s.status]?.ar ?? s.status}</Pill> },
          ]} />
        )}
      </div>

      <SideSheet open={active !== null} onClose={() => setActive(null)} title={`حسم نقص #${active?.id ?? ''}`}>
        <div className="flex flex-col gap-space-lg">
          <div className="flex flex-col gap-space-xs">
            <span className="font-small text-small text-secondary">الطرف المسؤول</span>
            {[
              { v: 'supplier', ar: 'مورد البضاعة' },
              { v: 'channel_partner', ar: 'وكيل التوزيع / الفرع المستلم' },
              { v: 'unallocated', ar: 'غير محدد / تلف أثناء النقل' },
            ].map((o) => (
              <label key={o.v} className="flex items-center gap-space-sm font-body text-body">
                <input type="radio" name="party" checked={party === o.v} onChange={() => setParty(o.v)} /> {o.ar}
              </label>
            ))}
          </div>
          {party === 'channel_partner' && (
            <Field label="معرّف الوكيل/الفرع" dir="ltr" mono inputMode="numeric" value={partyId} onChange={(e) => setPartyId(e.target.value)} required />
          )}
          <Field label="سبب القرار (إلزامي، ٥ أحرف فأكثر)" value={reason} onChange={(e) => setReason(e.target.value)} required minLength={5} />
          <Button variant="primary" onClick={onResolve} disabled={busy || reason.trim().length < 5}>حسم وترحيل القيد</Button>
        </div>
      </SideSheet>
    </Wide>
  )
}

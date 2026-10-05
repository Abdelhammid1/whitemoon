import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { SideSheet } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { listShortages, reportShortage, resolveShortage, type Shortage } from '../../api/inventory'
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
  // Report (create) shortage
  const [reportOpen, setReportOpen] = useState(false)
  const [rform, setRform] = useState({ product_id: '', supplier_id: '', qty: '', unit_cost: '', transfer_order_id: '', evidence: '' })
  const [rerror, setRerror] = useState<string | null>(null)

  function parseEvidence(raw: string): string[] {
    return raw.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean)
  }

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

  async function onReport() {
    setRerror(null)
    const keys = parseEvidence(rform.evidence)
    if (keys.length === 0) {
      setRerror('إثبات مصوّر إلزامي — أدخل مفتاح صورة واحدًا على الأقل.')
      return
    }
    if (!rform.product_id || !rform.supplier_id || !rform.qty || !rform.unit_cost) {
      setRerror('أكمل بيانات المنتج والمورد والكمية والتكلفة.')
      return
    }
    setBusy(true)
    try {
      await reportShortage({
        product_id: Number(rform.product_id),
        supplier_id: Number(rform.supplier_id),
        qty: Number(rform.qty),
        unit_cost: Number(rform.unit_cost),
        evidence_s3_keys: keys,
        ...(rform.transfer_order_id ? { transfer_order_id: Number(rform.transfer_order_id) } : {}),
      })
      toast.success('تم تسجيل بلاغ النقص.')
      setReportOpen(false)
      setRform({ product_id: '', supplier_id: '', qty: '', unit_cost: '', transfer_order_id: '', evidence: '' })
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل التسجيل')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Wide>
      <div className="flex items-start justify-between">
        <PageTitle title="النواقص والمرتجعات" subtitle="تُحسم القيمة من الطرف المسؤول، ويُرحَّل القيد تلقائيًا." />
        <Button variant="primary" onClick={() => { setRerror(null); setReportOpen(true) }} iconRight="add">بلاغ نقص جديد</Button>
      </div>

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

      <SideSheet open={reportOpen} onClose={() => setReportOpen(false)} title="بلاغ نقص جديد">
        <div className="flex flex-col gap-space-lg">
          <div className="grid grid-cols-2 gap-space-md">
            <Field label="رقم المنتج" dir="ltr" mono inputMode="numeric" value={rform.product_id} onChange={(e) => setRform({ ...rform, product_id: e.target.value })} required />
            <Field label="رقم المورد" dir="ltr" mono inputMode="numeric" value={rform.supplier_id} onChange={(e) => setRform({ ...rform, supplier_id: e.target.value })} required />
          </div>
          <div className="grid grid-cols-2 gap-space-md">
            <Field label="الكمية الناقصة" dir="ltr" mono inputMode="decimal" value={rform.qty} onChange={(e) => setRform({ ...rform, qty: e.target.value })} required />
            <Field label="تكلفة الوحدة" dir="ltr" mono inputMode="decimal" value={rform.unit_cost} onChange={(e) => setRform({ ...rform, unit_cost: e.target.value })} required />
          </div>
          <Field label="رقم إذن التحويل (اختياري)" dir="ltr" mono inputMode="numeric" value={rform.transfer_order_id} onChange={(e) => setRform({ ...rform, transfer_order_id: e.target.value })} />
          <div className="flex flex-col gap-space-xs">
            <label className="font-small text-small text-secondary">مفاتيح الإثبات المصوّر (إلزامي) — مفتاح لكل سطر أو مفصولة بفاصلة</label>
            <textarea
              className="bg-transparent border border-surface-container-high rounded-lg p-space-sm font-mono-body text-mono-body focus:outline-none focus:border-primary min-h-[72px]"
              dir="ltr"
              value={rform.evidence}
              onChange={(e) => setRform({ ...rform, evidence: e.target.value })}
              placeholder="receipts/2026/abc.jpg"
            />
          </div>
          {rerror && <InlineError message={rerror} />}
          <Button variant="primary" onClick={onReport} disabled={busy}>تسجيل البلاغ</Button>
        </div>
      </SideSheet>
    </Wide>
  )
}

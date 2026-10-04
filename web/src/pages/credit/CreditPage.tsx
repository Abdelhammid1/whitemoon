import { useState, type FormEvent } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, SectionHeader, Spinner, EmptyState } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import {
  getCustomerCredit, recomputeCredit, setOverride, listEscalations, freezeCustomer,
  type CreditTier, type Escalation,
} from '../../api/credit'
import { ApiError } from '../../api/client'
import { formatDate, formatMoney } from '../../lib/format'

const TIER: Record<string, { ar: string; tone: 'signal' | 'warning' | 'error' | 'neutral' }> = {
  green: { ar: 'أخضر', tone: 'signal' },
  white: { ar: 'أبيض', tone: 'neutral' },
  yellow: { ar: 'أصفر', tone: 'warning' },
  red: { ar: 'أحمر', tone: 'error' },
}

export function CreditPage() {
  const toast = useToast()
  const [cid, setCid] = useState('')
  const [tier, setTier] = useState<CreditTier | null>(null)
  const [escs, setEscs] = useState<Escalation[]>([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [modal, setModal] = useState<null | 'override' | 'freeze'>(null)
  const [limit, setLimit] = useState('')
  const [reason, setReason] = useState('')

  async function load(id: number) {
    setLoading(true)
    try {
      const [t, e] = await Promise.all([getCustomerCredit(id), listEscalations(id)])
      setTier(t); setEscs(e.items)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر التحميل'); setTier(null)
    } finally { setLoading(false) }
  }

  function onLookup(e: FormEvent) { e.preventDefault(); if (cid) void load(Number(cid)) }

  async function act(fn: () => Promise<unknown>, msg: string) {
    setBusy(true)
    try { await fn(); toast.success(msg); if (tier) await load(tier.customer_id) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشلت العملية') }
    finally { setBusy(false); setModal(null); setReason(''); setLimit('') }
  }

  return (
    <Narrow>
      <PageTitle title="التصنيف الائتماني" subtitle="استعرض ملف عميل ائتمانيًا: التصنيف اللوني، السقف، والذمم." />
      <form onSubmit={onLookup} className="mt-space-lg flex items-end gap-space-md">
        <div className="w-56"><Field label="رقم العميل" dir="ltr" mono inputMode="numeric" value={cid} onChange={(e) => setCid(e.target.value)} /></div>
        <Button variant="primary" type="submit" disabled={!cid}>عرض</Button>
      </form>

      {loading ? <div className="mt-space-xl"><Spinner /></div> : tier && (
        <>
          <section className="mt-space-xl flex flex-wrap items-center gap-space-md">
            <Pill tone={TIER[tier.tier]?.tone ?? 'neutral'}>{TIER[tier.tier]?.ar ?? tier.tier}</Pill>
            <span className="font-body text-body text-secondary">الدرجة <Mono>{tier.score ?? '—'}</Mono></span>
          </section>
          <section className="mt-space-md flex flex-col">
            {[
              ['السقف الافتراضي', tier.credit_limit_default],
              ['السقف الفعّال', tier.effective_limit],
              ['نسبة الآجل %', tier.deferred_pct],
              ['المستحق الحالي', tier.outstanding],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between py-space-sm border-b border-surface-container-high">
                <span className="font-small text-small text-secondary">{k}</span>
                <span className="font-body text-body"><Mono>{formatMoney(v)}</Mono></span>
              </div>
            ))}
          </section>
          <section className="mt-space-lg flex flex-wrap justify-end gap-space-sm">
            <Button onClick={() => act(() => recomputeCredit(tier.customer_id), 'أُعيد الاحتساب.')} disabled={busy}>إعادة الاحتساب</Button>
            <Button onClick={() => setModal('override')} disabled={busy}>استثناء على السقف</Button>
            <Button variant="destructive" onClick={() => setModal('freeze')} disabled={busy}>تجميد (مستوى ٥)</Button>
          </section>

          <section className="mt-[48px]">
            <SectionHeader title="سجل التصعيد" />
            {escs.length === 0 ? <EmptyState title="لا يوجد تصعيد." /> : (
              <DataTable rows={escs} rowKey={(e) => e.id} columns={[
                { header: 'المستوى', cell: (e) => <Mono>{e.level}</Mono> },
                { header: 'السبب', cell: (e) => e.trigger_reason },
                { header: 'تلقائي', align: 'center', cell: (e) => (e.is_automatic ? 'نعم' : 'يدوي') },
                { header: 'التاريخ', align: 'end', cell: (e) => <Mono>{formatDate(e.triggered_at)}</Mono> },
              ]} />
            )}
          </section>
        </>
      )}

      <Modal open={modal === 'override'} onClose={() => setModal(null)} title="استثناء على السقف الائتماني"
        footer={<><Button onClick={() => setModal(null)}>إلغاء</Button>
          <Button variant="primary" disabled={busy || !limit || reason.trim().length < 5}
            onClick={() => tier && act(() => setOverride(tier.customer_id, limit, reason), 'طُبّق الاستثناء.')}>تأكيد</Button></>}>
        <div className="flex flex-col gap-space-md">
          <Field label="السقف الجديد (ج.م)" dir="ltr" mono value={limit} onChange={(e) => setLimit(e.target.value)} />
          <Field label="السبب (٥ أحرف فأكثر)" value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </Modal>

      <Modal open={modal === 'freeze'} onClose={() => setModal(null)} title="تجميد الحساب (المستوى ٥)"
        footer={<><Button onClick={() => setModal(null)}>إلغاء</Button>
          <Button variant="destructive" disabled={busy || reason.trim().length < 5}
            onClick={() => tier && act(() => freezeCustomer(tier.customer_id, reason), 'تم التجميد.')}>تأكيد التجميد</Button></>}>
        <Field label="سبب التجميد (إلزامي)" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>
    </Narrow>
  )
}

import { useState, type FormEvent } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { Button, Field, Pill, Spinner, EmptyState } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import {
  getCustomerCredit, recomputeCredit, setOverride, listEscalations, freezeCustomer,
  listDues, payDue,
  type CreditTier, type Escalation, type Due,
} from '../../api/credit'
import { ApiError } from '../../api/client'
import { formatDate, formatMoney, todayIso } from '../../lib/format'

/* due status → Arabic label + pill tone */
const DUE_STATUS: Record<string, { ar: string; tone: 'signal' | 'warning' | 'error' | 'neutral' }> = {
  open: { ar: 'مفتوحة', tone: 'warning' },
  paid: { ar: 'مسدّدة', tone: 'signal' },
  defaulted: { ar: 'متعثّرة', tone: 'error' },
}

/* four-colour tier system → Arabic label + dot/tint classes (signals only) */
const TIER: Record<string, { ar: string; dot: string; tint: string }> = {
  green: { ar: 'أخضر (ممتاز)', dot: 'bg-[#0F6B3E]', tint: 'bg-[rgba(15,107,62,0.08)] text-[#0F6B3E]' },
  white: { ar: 'أبيض (تجريبي)', dot: 'bg-outline-variant', tint: 'bg-surface-container text-secondary' },
  yellow: { ar: 'أصفر (مراقبة)', dot: 'bg-[#A8650C]', tint: 'bg-[rgba(168,101,12,0.08)] text-[#A8650C]' },
  red: { ar: 'أحمر (محظور آجل)', dot: 'bg-[#ba1a1a]', tint: 'bg-[rgba(186,26,26,0.08)] text-[#ba1a1a]' },
}

/** Stitch-style metric card: label + icon, large mono value, unit. */
function StatCard({ label, value, icon, tone = 'primary', unit = 'ج.م' }: { label: string; value: string; icon: string; tone?: 'primary' | 'error'; unit?: string }) {
  return (
    <div className="p-space-md bg-surface-container-low rounded-lg flex flex-col justify-between min-h-[108px]">
      <div className="flex items-center justify-between text-secondary">
        <span className="font-small text-small">{label}</span>
        <Icon name={icon} size={16} />
      </div>
      <div className="mt-space-sm flex items-baseline gap-1" dir="ltr">
        <span className={`font-mono-medium text-display ${tone === 'error' ? 'text-[#ba1a1a]' : 'text-primary'}`}>{value}</span>
        <span className="font-mono-body text-mono-body text-secondary">{unit}</span>
      </div>
    </div>
  )
}

export function CreditPage() {
  const toast = useToast()
  const [cid, setCid] = useState('')
  const [tier, setTier] = useState<CreditTier | null>(null)
  const [escs, setEscs] = useState<Escalation[]>([])
  const [dues, setDues] = useState<Due[]>([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [modal, setModal] = useState<null | 'override' | 'freeze' | 'pay'>(null)
  const [limit, setLimit] = useState('')
  const [reason, setReason] = useState('')
  const [payDueId, setPayDueId] = useState<number | null>(null)
  const [paidOn, setPaidOn] = useState(todayIso())

  async function load(id: number) {
    setLoading(true)
    try {
      const [t, e, d] = await Promise.all([getCustomerCredit(id), listEscalations(id), listDues(id)])
      setTier(t); setEscs(e.items); setDues(d.items)
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

  const t = tier ? (TIER[tier.tier] ?? { ar: tier.tier, dot: 'bg-secondary', tint: 'bg-surface-container text-secondary' }) : null

  return (
    <Narrow>
      {/* Header + lookup */}
      <section className="flex flex-col gap-space-md pb-space-lg mb-space-xl border-b border-surface-container-highest">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-space-md">
          <div className="flex flex-col">
            <div className="flex items-center gap-space-xs text-secondary font-mono-medium text-mono-medium tracking-wide" dir="ltr">
              <span>PORTFOLIO_RISK_CONTROL</span>
              {tier && (
                <>
                  <span className="text-outline">/</span>
                  <span>CUSTOMER #{tier.customer_id}</span>
                </>
              )}
            </div>
            <h1 className="font-display text-display text-primary tracking-tight mt-space-xs">التصنيف والرقابة الائتمانية</h1>
            <p className="font-body text-body text-secondary mt-space-xs max-w-[620px]">
              استعرض الملف الائتماني لعميل: التصنيف اللوني، الدرجة، السقف، ونسبة الآجل والمستحق. كل القيم بالجنيه المصري.
            </p>
          </div>
          <form onSubmit={onLookup} className="flex items-center gap-space-sm w-full md:w-auto">
            <div className="relative flex-1 md:w-60 bg-surface-container-low px-space-md py-1.5 rounded flex items-center">
              <Icon name="search" size={18} className="text-secondary ml-space-xs shrink-0" />
              <input
                dir="ltr"
                inputMode="numeric"
                value={cid}
                onChange={(e) => setCid(e.target.value)}
                placeholder="رقم العميل"
                className="w-full bg-transparent text-primary font-mono-body text-mono-body placeholder:text-outline focus:outline-none"
              />
            </div>
            <Button variant="primary" type="submit" disabled={!cid} className="shrink-0">عرض</Button>
          </form>
        </div>
      </section>

      {loading ? <div className="mt-space-xl"><Spinner /></div> : tier && t && (
        <>
          {/* Red block banner (only for this customer when red) */}
          {tier.tier === 'red' && (
            <div className="bg-[#ffdad6] text-[#93000a] p-space-md rounded-lg flex items-center gap-space-sm mb-space-xl">
              <Icon name="emergency_home" size={20} className="shrink-0" />
              <div className="flex flex-col">
                <span className="font-body-medium text-body-medium">حظر البيع الآجل مفعّل لهذا العميل</span>
                <span className="font-small text-small">يمنع النظام تلقائياً إصدار أي أمر بيع آجل. التعامل نقدي أو إيداع مسبق فقط.</span>
              </div>
            </div>
          )}

          {/* Automatic overdue-escalation banner (independent of tier) */}
          {tier.order_block_level >= 4 ? (
            <div className="bg-[#ffdad6] text-[#93000a] p-space-md rounded-lg flex items-center gap-space-sm mb-space-xl">
              <Icon name="block" size={20} className="shrink-0" />
              <div className="flex flex-col">
                <span className="font-body-medium text-body-medium">تجميد الطلبات — تصعيد المستوى ٤</span>
                <span className="font-small text-small">يرفض النظام أي طلب جديد (نقدي أو آجل) حتى تسوية المتأخرات ولو جزئياً.</span>
              </div>
            </div>
          ) : tier.order_block_level >= 2 ? (
            <div className="bg-[rgba(168,101,12,0.08)] text-[#A8650C] p-space-md rounded-lg flex items-center gap-space-sm mb-space-xl">
              <Icon name="warning" size={20} className="shrink-0" />
              <div className="flex flex-col">
                <span className="font-body-medium text-body-medium">تخفيض السقف — تصعيد المستوى ٢</span>
                <span className="font-small text-small">خُفض السقف الفعّال ٥٠٪ ومُنع البيع الآجل الجديد بسبب تأخر السداد. يُرفع تلقائياً عند التسوية.</span>
              </div>
            </div>
          ) : null}

          {/* Tier + score */}
          <section className="flex flex-wrap items-center gap-space-md mb-space-lg">
            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full font-mono-medium text-mono-medium ${t.tint}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${t.dot}`} />
              <span>{t.ar}</span>
            </span>
            <span className="font-small text-small text-secondary">التقييم</span>
            <span className="font-mono-medium text-mono-medium text-primary bg-surface-container px-2 py-0.5 rounded" dir="ltr">
              {tier.score ?? '--'}
            </span>
          </section>

          {/* Metric strip — this customer's figures */}
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md mb-space-xl">
            <StatCard label="السقف الافتراضي" value={formatMoney(tier.credit_limit_default)} icon="account_balance_wallet" />
            <StatCard label="السقف الفعّال" value={formatMoney(tier.effective_limit)} icon="verified" />
            <StatCard label="نسبة الآجل" value={tier.deferred_pct} icon="pie_chart" unit="%" />
            <StatCard label="المستحق القائم" value={formatMoney(tier.outstanding)} icon="hourglass_top" tone="error" />
          </section>

          {/* Actions */}
          <section className="flex flex-wrap justify-end gap-space-sm mb-[48px]">
            <Button onClick={() => act(() => recomputeCredit(tier.customer_id), 'أُعيد الاحتساب.')} disabled={busy} iconRight="sync">إعادة الاحتساب</Button>
            <Button onClick={() => setModal('override')} disabled={busy}>استثناء على السقف</Button>
            <Button variant="destructive" onClick={() => setModal('freeze')} disabled={busy}>تجميد (مستوى ٥)</Button>
          </section>

          {/* Dues ledger */}
          <section className="mb-[48px]">
            <div className="flex items-center justify-between pb-space-sm mb-space-xs">
              <div className="flex flex-col">
                <span className="font-headline-2 text-headline-2 text-primary">الذمم</span>
                <span className="font-small text-small text-secondary">أرصدة البيع الآجل القائمة والمسوّاة لهذا العميل</span>
              </div>
            </div>
            {dues.length === 0 ? <EmptyState title="لا توجد ذمم." /> : (
              <DataTable rows={dues} rowKey={(d) => d.id} columns={[
                { header: 'التاريخ', cell: (d) => <Mono>{formatDate(d.due_date)}</Mono> },
                { header: 'الطلب', cell: (d) => (d.order_id != null ? <Mono>#{d.order_id}</Mono> : <span className="text-secondary">—</span>) },
                { header: 'المبلغ', align: 'end', cell: (d) => <span dir="ltr"><Mono>{formatMoney(d.amount)}</Mono> ج.م</span> },
                {
                  header: 'الحالة',
                  align: 'center',
                  cell: (d) => {
                    const s = DUE_STATUS[d.status] ?? { ar: d.status, tone: 'neutral' as const }
                    return <Pill tone={s.tone}>{s.ar}</Pill>
                  },
                },
                {
                  header: '',
                  align: 'end',
                  cell: (d) => (d.status === 'open'
                    ? <Button disabled={busy} onClick={() => { setPayDueId(d.id); setPaidOn(todayIso()); setModal('pay') }}>تسجيل سداد</Button>
                    : null),
                },
              ]} />
            )}
          </section>

          {/* Escalation / exception log */}
          <section>
            <div className="flex items-center justify-between pb-space-sm mb-space-xs">
              <div className="flex flex-col">
                <span className="font-headline-2 text-headline-2 text-primary">سجل قرارات الاستثناء والتصعيد</span>
                <span className="font-small text-small text-secondary">مسار التدقيق المالي المعتمد لقرارات مسؤولي الائتمان</span>
              </div>
            </div>
            {escs.length === 0 ? <EmptyState title="لا يوجد تصعيد." /> : (
              <DataTable rows={escs} rowKey={(e) => e.id} columns={[
                {
                  header: 'المستوى',
                  align: 'center',
                  cell: (e) => (
                    <span className={`font-mono-medium text-mono-medium px-1.5 py-0.5 rounded ${e.level >= 5 ? 'bg-[#ffdad6] text-[#ba1a1a]' : e.level >= 3 ? 'bg-[rgba(168,101,12,0.1)] text-[#A8650C]' : 'bg-surface-container text-primary'}`} dir="ltr">
                      L{e.level}
                    </span>
                  ),
                },
                { header: 'نوع الإجراء / المسوغ', cell: (e) => e.trigger_reason },
                { header: 'تلقائي', align: 'center', cell: (e) => (e.is_automatic ? 'آلي' : 'يدوي') },
                { header: 'التاريخ', align: 'end', cell: (e) => <Mono>{formatDate(e.triggered_at)}</Mono> },
              ]} />
            )}
          </section>
        </>
      )}

      <Modal open={modal === 'override'} onClose={() => setModal(null)} title="استثناء على السقف الائتماني"
        footer={<><Button onClick={() => setModal(null)}>إلغاء</Button>
          <Button variant="primary" disabled={busy || !limit || reason.trim().length < 5}
            onClick={() => tier && act(() => setOverride(tier.customer_id, limit, reason), 'طُبّق الاستثناء.')}>حفظ واعتماد الاستثناء</Button></>}>
        <div className="flex flex-col gap-space-md">
          <Field label="السقف الجديد (ج.م)" dir="ltr" mono value={limit} onChange={(e) => setLimit(e.target.value)} />
          <Field label="مسوغ الاستثناء الإلزامي (٥ أحرف فأكثر)" value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </Modal>

      <Modal open={modal === 'freeze'} onClose={() => setModal(null)} title="تجميد الحساب (المستوى ٥)"
        footer={<><Button onClick={() => setModal(null)}>إلغاء</Button>
          <Button variant="destructive" disabled={busy || reason.trim().length < 5}
            onClick={() => tier && act(() => freezeCustomer(tier.customer_id, reason), 'تم التجميد.')}>تأكيد التجميد</Button></>}>
        <Field label="سبب التجميد (إلزامي)" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>

      <Modal open={modal === 'pay'} onClose={() => setModal(null)} title="تسجيل سداد ذمّة"
        footer={<><Button onClick={() => setModal(null)}>إلغاء</Button>
          <Button variant="primary" disabled={busy || !paidOn || payDueId == null}
            onClick={() => payDueId != null && act(() => payDue(payDueId, paidOn), 'سُجِّل السداد.')}>تأكيد السداد</Button></>}>
        <Field label="تاريخ السداد" type="date" dir="ltr" mono value={paidOn} onChange={(e) => setPaidOn(e.target.value)} />
      </Modal>
    </Narrow>
  )
}

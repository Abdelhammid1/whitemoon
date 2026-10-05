import { useState, type FormEvent, type ReactNode } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { Button, Field, Pill, Dot, Card, Spinner, EmptyState } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import {
  getCustomerCredit, recomputeCredit, setOverride, listEscalations, freezeCustomer,
  listDues, payDue,
  type CreditTier, type Escalation, type Due,
} from '../../api/credit'
import { customerStatement, type CustomerStatement } from '../../api/commerce'
import { ApiError } from '../../api/client'
import { formatDate, formatMoney, todayIso } from '../../lib/format'

type Tone = 'signal' | 'warning' | 'error' | 'neutral'

/* due status → Arabic label + pill tone */
const DUE_STATUS: Record<string, { ar: string; tone: Tone }> = {
  open: { ar: 'مفتوحة', tone: 'warning' },
  paid: { ar: 'مسدّدة', tone: 'signal' },
  defaulted: { ar: 'متعثّرة', tone: 'error' },
}

/* four-colour tier system → Arabic label + signal tone (green→signal,
 * yellow→warning, red→error, white/new→neutral). */
const TIER_TONE: Record<string, Tone> = { green: 'signal', white: 'neutral', yellow: 'warning', red: 'error' }
const TIER_AR: Record<string, string> = {
  green: 'أخضر (ممتاز)', white: 'أبيض (تجريبي)', yellow: 'أصفر (مراقبة)', red: 'أحمر (محظور آجل)',
}

/** KPI tile: icon chip, large mono value + unit, label. */
function StatCard({ label, value, icon, tone = 'neutral', unit = 'ج.م' }: {
  label: string; value: string; icon: string; tone?: 'neutral' | 'error'; unit?: string
}) {
  const chip = tone === 'error' ? 'bg-danger-weak text-danger' : 'bg-brand-weak text-primary'
  return (
    <Card className="flex flex-col gap-space-md min-h-[128px]">
      <span className={`w-10 h-10 rounded-xl flex items-center justify-center ${chip}`}>
        <Icon name={icon} size={20} />
      </span>
      <div className="flex flex-col gap-0.5">
        <div className="flex items-baseline gap-1" dir="ltr">
          <span className={`font-mono-medium text-display tracking-tight ${tone === 'error' ? 'text-danger' : 'text-on-surface'}`}>{value}</span>
          <span className="font-small text-small text-secondary">{unit}</span>
        </div>
        <span className="font-small text-small text-secondary">{label}</span>
      </div>
    </Card>
  )
}

/** Tier-coloured alert banner (token tints only). */
function Banner({ tone, icon, title, children }: { tone: 'error' | 'warning'; icon: string; title: string; children: ReactNode }) {
  const cls = tone === 'error'
    ? 'bg-danger-weak text-danger border-danger/30'
    : 'bg-warning-weak text-warning border-warning/30'
  return (
    <div className={`flex items-start gap-space-sm rounded-2xl border p-space-md mb-space-xl ${cls}`}>
      <Icon name={icon} size={20} className="shrink-0 mt-0.5" />
      <div className="flex flex-col">
        <span className="font-body-medium text-body-medium">{title}</span>
        <span className="font-small text-small">{children}</span>
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
  const [modal, setModal] = useState<null | 'override' | 'freeze' | 'pay' | 'statement'>(null)
  const [statement, setStatement] = useState<CustomerStatement | null>(null)
  const [stmtLoading, setStmtLoading] = useState(false)
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

  async function openStatement(customerId: number) {
    setModal('statement'); setStatement(null); setStmtLoading(true)
    try { setStatement(await customerStatement(customerId)) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر تحميل كشف الحساب') }
    finally { setStmtLoading(false) }
  }

  async function act(fn: () => Promise<unknown>, msg: string) {
    setBusy(true)
    try { await fn(); toast.success(msg); if (tier) await load(tier.customer_id) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشلت العملية') }
    finally { setBusy(false); setModal(null); setReason(''); setLimit('') }
  }

  const tierTone = tier ? (TIER_TONE[tier.tier] ?? 'neutral') : 'neutral'
  const tierAr = tier ? (TIER_AR[tier.tier] ?? tier.tier) : ''

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
            <h1 className="font-display text-display text-primary font-medium tracking-tight mt-space-xs">التصنيف والرقابة الائتمانية</h1>
            <p className="font-body text-body text-secondary mt-space-xs max-w-[620px]">
              استعرض الملف الائتماني لعميل: التصنيف اللوني، الدرجة، السقف، ونسبة الآجل والمستحق. كل القيم بالجنيه المصري.
            </p>
          </div>
          <form onSubmit={onLookup} className="flex items-center gap-space-sm w-full md:w-auto">
            <div className="relative flex-1 md:w-60 bg-surface-container-low px-space-md py-1.5 rounded-lg flex items-center">
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

      {loading ? <div className="mt-space-xl"><Spinner /></div> : tier && (
        <>
          {/* Red block banner (only for this customer when red) */}
          {tier.tier === 'red' && (
            <Banner tone="error" icon="emergency_home" title="حظر البيع الآجل مفعّل لهذا العميل">
              يمنع النظام تلقائياً إصدار أي أمر بيع آجل. التعامل نقدي أو إيداع مسبق فقط.
            </Banner>
          )}

          {/* Automatic overdue-escalation banner (independent of tier) */}
          {tier.order_block_level >= 4 ? (
            <Banner tone="error" icon="block" title="تجميد الطلبات — تصعيد المستوى ٤">
              يرفض النظام أي طلب جديد (نقدي أو آجل) حتى تسوية المتأخرات ولو جزئياً.
            </Banner>
          ) : tier.order_block_level >= 2 ? (
            <Banner tone="warning" icon="warning" title="تخفيض السقف — تصعيد المستوى ٢">
              خُفض السقف الفعّال ٥٠٪ ومُنع البيع الآجل الجديد بسبب تأخر السداد. يُرفع تلقائياً عند التسوية.
            </Banner>
          ) : null}

          {/* Tier + score */}
          <section className="flex flex-wrap items-center gap-space-md mb-space-lg">
            <span className="inline-flex items-center gap-space-xs">
              <Dot tone={tierTone} />
              <Pill tone={tierTone}>{tierAr}</Pill>
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
            <StatCard label="نسبة الآجل" value={String(Number(tier.deferred_pct))} icon="pie_chart" unit="%" />
            <StatCard label="المستحق القائم" value={formatMoney(tier.outstanding)} icon="hourglass_top" tone="error" />
          </section>

          {/* Actions */}
          <section className="flex flex-wrap justify-end gap-space-sm mb-[48px]">
            <Button onClick={() => act(() => recomputeCredit(tier.customer_id), 'أُعيد الاحتساب.')} disabled={busy} iconRight="sync">إعادة الاحتساب</Button>
            <Button onClick={() => void openStatement(tier.customer_id)} disabled={busy} iconRight="receipt_long">كشف الحساب</Button>
            <Button onClick={() => setModal('override')} disabled={busy}>استثناء على السقف</Button>
            <Button variant="destructive" onClick={() => setModal('freeze')} disabled={busy}>تجميد (مستوى ٥)</Button>
          </section>

          {/* Dues ledger */}
          <section className="mb-[48px]">
            <div className="flex items-center justify-between pb-space-sm mb-space-md">
              <div className="flex flex-col">
                <span className="font-headline-2 text-headline-2 text-primary">الذمم</span>
                <span className="font-small text-small text-secondary">أرصدة البيع الآجل القائمة والمسوّاة لهذا العميل</span>
              </div>
            </div>
            {dues.length === 0 ? <EmptyState title="لا توجد ذمم." /> : (
              <Card padded={false} className="overflow-hidden">
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
              </Card>
            )}
          </section>

          {/* Escalation / exception log */}
          <section>
            <div className="flex items-center justify-between pb-space-sm mb-space-md">
              <div className="flex flex-col">
                <span className="font-headline-2 text-headline-2 text-primary">سجل قرارات الاستثناء والتصعيد</span>
                <span className="font-small text-small text-secondary">مسار التدقيق المالي المعتمد لقرارات مسؤولي الائتمان</span>
              </div>
            </div>
            {escs.length === 0 ? <EmptyState title="لا يوجد تصعيد." /> : (
              <Card padded={false} className="overflow-hidden">
                <DataTable rows={escs} rowKey={(e) => e.id} columns={[
                  {
                    header: 'المستوى',
                    align: 'center',
                    cell: (e) => <Pill tone={e.level >= 5 ? 'error' : e.level >= 3 ? 'warning' : 'brand'}>مستوى {e.level}</Pill>,
                  },
                  { header: 'نوع الإجراء / المسوغ', cell: (e) => e.trigger_reason },
                  { header: 'تلقائي', align: 'center', cell: (e) => (e.is_automatic ? <Pill tone="neutral">آلي</Pill> : <Pill tone="gold">يدوي</Pill>) },
                  { header: 'التاريخ', align: 'end', cell: (e) => <Mono>{formatDate(e.triggered_at)}</Mono> },
                ]} />
              </Card>
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

      <Modal open={modal === 'statement'} onClose={() => setModal(null)} title="كشف حساب العميل"
        footer={<Button onClick={() => setModal(null)}>إغلاق</Button>}>
        {stmtLoading ? <Spinner /> : !statement ? <EmptyState title="لا توجد بيانات." /> : (
          <div className="flex flex-col gap-space-md">
            <Card className="flex flex-wrap items-center gap-space-md">
              <span className="font-body-medium text-body-medium text-primary">
                {statement.profile.display_name ?? `عميل #${statement.customer_id}`}
              </span>
              {statement.profile.geo_area && (
                <span className="font-small text-small text-secondary">{statement.profile.geo_area}</span>
              )}
              <span className="ml-auto inline-flex items-baseline gap-1 font-mono-medium text-mono-medium text-danger" dir="ltr">
                <Mono>{formatMoney(statement.outstanding)}</Mono>
                <span className="text-secondary">ج.م مستحق</span>
              </span>
            </Card>

            <Card className="flex flex-col gap-space-sm">
              <span className="font-small-medium text-small-medium text-secondary">الطلبات</span>
              {statement.orders.length === 0 ? (
                <p className="font-small text-small text-secondary">لا توجد طلبات.</p>
              ) : (
                <DataTable rows={statement.orders} rowKey={(o) => o.id} columns={[
                  { header: 'الطلب', cell: (o) => <Mono>{o.number}</Mono> },
                  { header: 'الحالة', align: 'center', cell: (o) => <span className="font-small text-small text-secondary">{o.status}</span> },
                  { header: 'آجل', align: 'end', cell: (o) => <span dir="ltr"><Mono>{formatMoney(o.total_deferred)}</Mono> ج.م</span> },
                  { header: 'نقدي', align: 'end', cell: (o) => <span dir="ltr"><Mono>{formatMoney(o.total_cash)}</Mono> ج.م</span> },
                ]} />
              )}
            </Card>

            <Card className="flex flex-col gap-space-sm">
              <span className="font-small-medium text-small-medium text-secondary">الذمم</span>
              {statement.dues.length === 0 ? (
                <p className="font-small text-small text-secondary">لا توجد ذمم.</p>
              ) : (
                <DataTable rows={statement.dues} rowKey={(d) => d.id} columns={[
                  { header: 'الاستحقاق', cell: (d) => <Mono>{formatDate(d.due_date)}</Mono> },
                  { header: 'المبلغ', align: 'end', cell: (d) => <span dir="ltr"><Mono>{formatMoney(d.amount)}</Mono> ج.م</span> },
                  { header: 'الحالة', align: 'center', cell: (d) => {
                    const s = DUE_STATUS[d.status] ?? { ar: d.status, tone: 'neutral' as const }
                    return <Pill tone={s.tone}>{s.ar}</Pill>
                  } },
                  { header: 'تأخّر', align: 'end', cell: (d) => <Mono>{d.days_late != null ? `${d.days_late} يوم` : '—'}</Mono> },
                ]} />
              )}
            </Card>
          </div>
        )}
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

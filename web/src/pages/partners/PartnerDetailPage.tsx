import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, SectionHeader, Spinner, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import {
  attributeOrder, computeAccrual, getAccrualStatement, getLedger, getTerms, listAccruals,
  listDeposits, recordDeposit, recordLedgerEntry, refundDeposit, setTerms,
  type Accrual, type AccrualStatement, type Deposit, type LedgerEntry, type LedgerSummary, type PartnerTerms,
} from '../../api/partners'
import { ApiError } from '../../api/client'
import { formatMoney, formatDate, todayIso } from '../../lib/format'

/* movement → Arabic label + balance-effect tone (+1 = partner owes us more) */
function ledgerLabel(e: LedgerEntry): string {
  if (e.kind === 'payment_made') return 'دفعنا له (نقد خارج)'
  if (e.kind === 'payment_received') return 'استلمنا منه (نقد داخل)'
  return e.direction > 0 ? 'تعديل يدوي — تحميل عليه' : 'تعديل يدوي — زيادة لصالحه'
}

export function PartnerDetailPage() {
  const { id } = useParams()
  const pid = Number(id)
  const toast = useToast()
  const [terms, setTermsState] = useState<PartnerTerms | null>(null)
  const [deposits, setDeposits] = useState<Deposit[]>([])
  const [accruals, setAccruals] = useState<Accrual[]>([])
  const [ledger, setLedger] = useState<LedgerSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [dep, setDep] = useState({ amount: '', recovery_conditions: '' })
  const [acc, setAcc] = useState({ kind: 'commission', year: String(new Date().getFullYear()), month: String(new Date().getMonth() + 1) })
  const [pay, setPay] = useState({ amount: '', note: '' })
  const [recv, setRecv] = useState({ amount: '', note: '' })
  const [adj, setAdj] = useState({ amount: '', note: '', direction: -1 }) // -1 = زوّده له
  const [attrOrderId, setAttrOrderId] = useState('')
  const [stmt, setStmt] = useState<{ open: boolean; loading: boolean; data: AccrualStatement | null }>({ open: false, loading: false, data: null })

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const [t, d, a, l] = await Promise.all([getTerms(pid), listDeposits(pid), listAccruals(pid), getLedger(pid)])
      setTermsState(t); setDeposits(d.items); setAccruals(a.items); setLedger(l)
    } catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [pid])
  useEffect(() => { void load() }, [load])

  async function run(fn: () => Promise<unknown>, msg: string) {
    setBusy(true)
    try { await fn(); toast.success(msg); await load() }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشلت العملية') }
    finally { setBusy(false) }
  }

  async function recordMove(
    body: Parameters<typeof recordLedgerEntry>[1],
    msg: string,
    reset: () => void,
  ) {
    setBusy(true)
    try {
      const r = await recordLedgerEntry(pid, body)
      setLedger(r); toast.success(msg); reset()
    } catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشلت العملية') }
    finally { setBusy(false) }
  }

  async function attribute() {
    setBusy(true)
    try {
      await attributeOrder(Number(attrOrderId), pid)
      toast.success('تم نسب الطلب.'); setAttrOrderId(''); await load()
    } catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشلت العملية') }
    finally { setBusy(false) }
  }

  async function openStatement(a: Accrual) {
    const [y, m] = a.period.split('/')
    setStmt({ open: true, loading: true, data: null })
    try {
      const data = await getAccrualStatement(pid, a.kind, Number(y), Number(m))
      setStmt({ open: true, loading: false, data })
    } catch (err) {
      setStmt({ open: false, loading: false, data: null })
      toast.error(err instanceof ApiError ? err.message : 'تعذّر تحميل الأساس')
    }
  }

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error || !terms) return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>

  return (
    <Narrow>
      <PageTitle title={`شريك #${pid}`} subtitle="الحساب الجاري والشروط والتأمينات والاستحقاقات." />

      {/* الحساب الجاري — current account */}
      <section className="mt-space-xl">
        <SectionHeader title="الحساب الجاري" action={ledger ? <span className="font-small text-small text-secondary">{ledger.count} حركة</span> : undefined} />

        {/* Balance banner */}
        {ledger && (
          <div className="mt-space-md p-space-lg bg-surface-container-low rounded-xl flex items-center justify-between gap-space-md">
            <span className="font-body text-body text-secondary">
              {ledger.owed_by === 'partner' ? 'عليه للإدارة' : ledger.owed_by === 'management' ? 'له عند الإدارة' : 'الحساب متزن'}
            </span>
            <div className="flex items-baseline gap-space-xs" dir="ltr">
              <span className={`font-mono-medium text-display ${ledger.owed_by === 'management' ? 'text-[#A8650C]' : ledger.owed_by === 'settled' ? 'text-[#0F6B3E]' : 'text-primary'}`}>
                {formatMoney(ledger.abs_balance)}
              </span>
              <span className="font-small text-small text-secondary">ج.م</span>
            </div>
          </div>
        )}

        {/* Money-movement forms */}
        <div className="mt-space-md grid grid-cols-1 md:grid-cols-3 gap-space-md">
          {/* دفعت له */}
          <div className="p-space-md border border-surface-container-high rounded-xl flex flex-col gap-space-sm">
            <span className="font-body-medium text-body-medium text-primary">دفعت له فلوس</span>
            <Field label="المبلغ (ج.م)" dir="ltr" mono value={pay.amount} onChange={(e) => setPay({ ...pay, amount: e.target.value })} />
            <Field label="ملاحظات (اختياري)" value={pay.note} onChange={(e) => setPay({ ...pay, note: e.target.value })} />
            <Button variant="primary" disabled={busy || !pay.amount}
              onClick={() => recordMove({ kind: 'payment_made', amount: Number(pay.amount), note: pay.note || undefined }, 'سُجِّلت الدفعة.', () => setPay({ amount: '', note: '' }))}>دفعت</Button>
          </div>
          {/* استلمت منه */}
          <div className="p-space-md border border-surface-container-high rounded-xl flex flex-col gap-space-sm">
            <span className="font-body-medium text-body-medium text-primary">استلمت منه فلوس</span>
            <Field label="المبلغ (ج.م)" dir="ltr" mono value={recv.amount} onChange={(e) => setRecv({ ...recv, amount: e.target.value })} />
            <Field label="ملاحظات (اختياري)" value={recv.note} onChange={(e) => setRecv({ ...recv, note: e.target.value })} />
            <Button variant="primary" disabled={busy || !recv.amount}
              onClick={() => recordMove({ kind: 'payment_received', amount: Number(recv.amount), note: recv.note || undefined }, 'سُجِّل الاستلام.', () => setRecv({ amount: '', note: '' }))}>استلمت</Button>
          </div>
          {/* تعديل يدوي */}
          <div className="p-space-md border border-surface-container-high rounded-xl flex flex-col gap-space-sm">
            <span className="font-body-medium text-body-medium text-primary">تعديل يدوي</span>
            <Field label="المبلغ (ج.م)" dir="ltr" mono value={adj.amount} onChange={(e) => setAdj({ ...adj, amount: e.target.value })} />
            <Field label="السبب (إلزامي، ٥ أحرف فأكثر)" value={adj.note} onChange={(e) => setAdj({ ...adj, note: e.target.value })} />
            <div className="flex gap-space-xs">
              {([[-1, 'زوّده له'], [1, 'حمّله عليه']] as const).map(([d, lbl]) => (
                <button key={d} type="button" onClick={() => setAdj({ ...adj, direction: d })}
                  className={`px-3 py-1 rounded-full font-small ${adj.direction === d ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant'}`}>{lbl}</button>
              ))}
            </div>
            <Button disabled={busy || !adj.amount || adj.note.trim().length < 5}
              onClick={() => recordMove({ kind: 'manual', amount: Number(adj.amount), direction: adj.direction, note: adj.note }, 'طُبّق التعديل.', () => setAdj({ amount: '', note: '', direction: -1 }))}>نفّذ</Button>
          </div>
        </div>

        {/* كل الحركات */}
        <div className="mt-space-md">
          <DataTable rows={ledger?.items ?? []} rowKey={(e) => e.id} empty="لا توجد حركات." columns={[
            { header: 'التاريخ', cell: (e) => <Mono>{e.created_at ? formatDate(e.created_at) : '—'}</Mono> },
            { header: 'البيان', cell: (e) => (
              <div className="flex flex-col">
                <span>{ledgerLabel(e)}</span>
                {e.note && <span className="font-small text-small text-secondary">{e.note}</span>}
              </div>
            ) },
            { header: 'الأثر', align: 'center', cell: (e) => (
              <Pill tone={e.direction > 0 ? 'warning' : 'signal'}>{e.direction > 0 ? 'عليه +' : 'له −'}</Pill>
            ) },
            { header: 'المبلغ', align: 'end', cell: (e) => <Mono>{formatMoney(e.amount)}</Mono> },
          ]} />
        </div>
      </section>

      <section className="mt-[48px]">
        <SectionHeader title="الشروط" />
        <div className="flex flex-wrap items-end gap-space-md">
          <label className="flex items-center gap-space-sm font-body text-body">
            <input type="checkbox" checked={terms.earns_commission} onChange={(e) => setTermsState({ ...terms, earns_commission: e.target.checked })} /> يستحق عمولة
          </label>
          <div className="w-28"><Field label="نسبة العمولة %" dir="ltr" mono value={terms.commission_rate_pct} onChange={(e) => setTermsState({ ...terms, commission_rate_pct: e.target.value })} /></div>
          <label className="flex items-center gap-space-sm font-body text-body">
            <input type="checkbox" checked={terms.earns_investment_return} onChange={(e) => setTermsState({ ...terms, earns_investment_return: e.target.checked })} /> عائد استثماري
          </label>
          <div className="w-28"><Field label="نسبة العائد %" dir="ltr" mono value={terms.investment_return_rate_pct} onChange={(e) => setTermsState({ ...terms, investment_return_rate_pct: e.target.value })} /></div>
          <Button variant="primary" disabled={busy} onClick={() => run(() => setTerms(pid, {
            earns_commission: terms.earns_commission, commission_rate_pct: Number(terms.commission_rate_pct),
            earns_investment_return: terms.earns_investment_return, investment_return_rate_pct: Number(terms.investment_return_rate_pct),
          }), 'حُفظت الشروط.')}>حفظ</Button>
        </div>
      </section>

      <section className="mt-[48px]">
        <SectionHeader title="التأمينات" />
        <div className="flex flex-wrap items-end gap-space-md mb-space-md">
          <div className="w-36"><Field label="المبلغ (ج.م)" dir="ltr" mono value={dep.amount} onChange={(e) => setDep({ ...dep, amount: e.target.value })} /></div>
          <div className="flex-1 min-w-[200px]"><Field label="شروط الاسترداد" value={dep.recovery_conditions} onChange={(e) => setDep({ ...dep, recovery_conditions: e.target.value })} /></div>
          <Button disabled={busy || !dep.amount || dep.recovery_conditions.length < 5}
            onClick={() => run(() => recordDeposit(pid, { amount: Number(dep.amount), deposit_date: todayIso(), recovery_conditions: dep.recovery_conditions }), 'سُجِّل التأمين.')}>تسجيل تأمين</Button>
        </div>
        <DataTable rows={deposits} rowKey={(d) => d.id} empty="لا توجد تأمينات." columns={[
          { header: 'المبلغ', align: 'end', cell: (d) => <Mono>{formatMoney(d.amount)}</Mono> },
          { header: 'التاريخ', cell: (d) => <Mono>{d.deposit_date}</Mono> },
          { header: 'الحالة', align: 'center', cell: (d) => <Pill tone={d.status === 'held' ? 'signal' : 'neutral'}>{d.status === 'held' ? 'محتجز' : 'مُسترد'}</Pill> },
          { header: '', align: 'end', cell: (d) => d.status === 'held'
            ? <button className="text-[#ba1a1a] font-small hover:underline" disabled={busy} onClick={() => run(() => refundDeposit(d.id, 'استرداد عند إنهاء التعاقد'), 'رُدّ التأمين.')}>رد</button>
            : null },
        ]} />
      </section>

      <section className="mt-[48px]">
        <SectionHeader title="الاستحقاقات" />

        {/* Attribute a realized order to this partner (feeds the accrual basis) */}
        <div className="flex flex-wrap items-end gap-space-md mb-space-md">
          <div className="w-36"><Field label="رقم الطلب" dir="ltr" mono value={attrOrderId} onChange={(e) => setAttrOrderId(e.target.value)} /></div>
          <Button disabled={busy || !attrOrderId} onClick={() => void attribute()}>نسب طلبًا لهذا الشريك</Button>
          <span className="font-small text-small text-secondary">يُسنِد طلبًا مُنفَّذًا لهذا الشريك ليدخل ضمن أساس احتساب العمولة والعائد.</span>
        </div>

        <div className="flex flex-wrap items-end gap-space-md mb-space-md">
          <div className="flex gap-space-xs pb-2">
            {(['commission', 'investment_return'] as const).map((k) => (
              <button key={k} onClick={() => setAcc({ ...acc, kind: k })}
                className={`px-3 py-1 rounded-full font-small ${acc.kind === k ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant'}`}>
                {k === 'commission' ? 'عمولة' : 'عائد'}
              </button>
            ))}
          </div>
          <div className="w-24"><Field label="السنة" dir="ltr" mono value={acc.year} onChange={(e) => setAcc({ ...acc, year: e.target.value })} /></div>
          <div className="w-20"><Field label="الشهر" dir="ltr" mono value={acc.month} onChange={(e) => setAcc({ ...acc, month: e.target.value })} /></div>
          <Button disabled={busy} onClick={() => run(() => computeAccrual(pid, acc.kind, Number(acc.year), Number(acc.month)), 'احتُسب الاستحقاق.')}>احتساب</Button>
        </div>
        <DataTable rows={accruals} rowKey={(a) => a.id} empty="لا توجد استحقاقات." columns={[
          { header: 'النوع', cell: (a) => (a.kind === 'commission' ? 'عمولة' : 'عائد') },
          { header: 'الفترة', cell: (a) => <Mono>{a.period}</Mono> },
          { header: 'الأساس', align: 'end', cell: (a) => <Mono>{formatMoney(a.basis_amount)}</Mono> },
          { header: 'النسبة %', align: 'end', cell: (a) => <Mono>{a.rate_pct}</Mono> },
          { header: 'المبلغ', align: 'end', cell: (a) => <Mono>{formatMoney(a.amount)}</Mono> },
          { header: '', align: 'end', cell: (a) => (
            <button className="font-small text-small text-primary hover:underline" onClick={() => void openStatement(a)}>عرض الأساس</button>
          ) },
        ]} />
      </section>

      {/* Accrual basis statement (US-6.2) */}
      <Modal open={stmt.open} onClose={() => setStmt({ open: false, loading: false, data: null })} title="أساس احتساب الاستحقاق">
        {stmt.loading || !stmt.data ? <Spinner /> : (
          <div className="flex flex-col gap-space-md">
            <div className="flex flex-wrap gap-space-lg">
              <div className="flex flex-col">
                <span className="font-small text-small text-secondary">النوع والفترة</span>
                <span className="font-body text-body">{stmt.data.kind === 'commission' ? 'عمولة' : 'عائد'} — <Mono>{stmt.data.period}</Mono></span>
              </div>
              <div className="flex flex-col">
                <span className="font-small text-small text-secondary">النسبة %</span>
                <Mono>{stmt.data.rate_pct}</Mono>
              </div>
              <div className="flex flex-col">
                <span className="font-small text-small text-secondary">الأساس</span>
                <span className="font-body text-body"><Mono>{formatMoney(stmt.data.basis_amount)}</Mono> ج.م</span>
              </div>
              <div className="flex flex-col">
                <span className="font-small text-small text-secondary">المبلغ المستحق</span>
                <span className="font-body text-body"><Mono>{formatMoney(stmt.data.accrual_amount)}</Mono> ج.م</span>
              </div>
            </div>
            <DataTable rows={stmt.data.orders} rowKey={(o) => o.id} empty="لا توجد طلبات مساهمة في هذه الفترة." columns={[
              { header: 'رقم الطلب', cell: (o) => o.number },
              { header: 'المعرف', cell: (o) => <Mono>#{o.id}</Mono> },
              { header: 'القيمة', align: 'end', cell: (o) => <span><Mono>{formatMoney(o.total_cash)}</Mono> ج.م</span> },
            ]} />
          </div>
        )}
      </Modal>
    </Narrow>
  )
}

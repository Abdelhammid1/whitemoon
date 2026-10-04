import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, SectionHeader, Spinner, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import {
  computeAccrual, getTerms, listAccruals, listDeposits, recordDeposit, refundDeposit, setTerms,
  type Accrual, type Deposit, type PartnerTerms,
} from '../../api/partners'
import { ApiError } from '../../api/client'
import { formatMoney, todayIso } from '../../lib/format'

export function PartnerDetailPage() {
  const { id } = useParams()
  const pid = Number(id)
  const toast = useToast()
  const [terms, setTermsState] = useState<PartnerTerms | null>(null)
  const [deposits, setDeposits] = useState<Deposit[]>([])
  const [accruals, setAccruals] = useState<Accrual[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [dep, setDep] = useState({ amount: '', recovery_conditions: '' })
  const [acc, setAcc] = useState({ kind: 'commission', year: String(new Date().getFullYear()), month: String(new Date().getMonth() + 1) })

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const [t, d, a] = await Promise.all([getTerms(pid), listDeposits(pid), listAccruals(pid)])
      setTermsState(t); setDeposits(d.items); setAccruals(a.items)
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

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error || !terms) return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>

  return (
    <Narrow>
      <PageTitle title={`شريك #${pid}`} subtitle="الشروط والتأمينات والاستحقاقات." />

      <section className="mt-space-xl">
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
        ]} />
      </section>
    </Narrow>
  )
}

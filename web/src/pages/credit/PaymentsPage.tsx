import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, SectionHeader, Spinner, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import {
  approvePayment, collectPayment, listPayments, rejectPayment, type PaymentApproval,
} from '../../api/credit'
import { ApiError } from '../../api/client'
import { formatMoney, todayIso } from '../../lib/format'

const STATUS: Record<string, { ar: string; tone: 'signal' | 'warning' | 'error' | 'neutral' }> = {
  pending: { ar: 'معلّق', tone: 'warning' },
  approved: { ar: 'معتمد', tone: 'signal' },
  rejected: { ar: 'مرفوض', tone: 'error' },
}

export function PaymentsPage() {
  const toast = useToast()
  const [rows, setRows] = useState<PaymentApproval[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [cid, setCid] = useState('')
  const [dueId, setDueId] = useState('')
  const [amount, setAmount] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setRows((await listPayments()).items) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  async function collect(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      await collectPayment({ customer_id: Number(cid), due_id: dueId ? Number(dueId) : undefined, amount, paid_on: todayIso() })
      toast.success('سُجِّل التحصيل بانتظار الاعتماد.')
      setCid(''); setDueId(''); setAmount('')
      await load()
    } catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل التحصيل') }
    finally { setBusy(false) }
  }

  async function act(fn: () => Promise<unknown>, msg: string) {
    setBusy(true)
    try { await fn(); toast.success(msg); await load() }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشلت العملية') }
    finally { setBusy(false) }
  }

  return (
    <Wide>
      <PageTitle title="اعتماد السداد" subtitle="تحصيل يُعتمد بمستوى واحد قبل الشركة — لا يعتمد المحصِّل تحصيله بنفسه." />

      <form onSubmit={collect} className="mt-space-lg flex flex-wrap items-end gap-space-md">
        <div className="w-40"><Field label="رقم العميل" dir="ltr" mono inputMode="numeric" value={cid} onChange={(e) => setCid(e.target.value)} required /></div>
        <div className="w-40"><Field label="رقم الذمة (اختياري)" dir="ltr" mono inputMode="numeric" value={dueId} onChange={(e) => setDueId(e.target.value)} /></div>
        <div className="w-40"><Field label="المبلغ (ج.م)" dir="ltr" mono value={amount} onChange={(e) => setAmount(e.target.value)} required /></div>
        <Button variant="primary" type="submit" disabled={busy || !cid || !amount}>تسجيل تحصيل</Button>
      </form>

      <section className="mt-[48px]">
        <SectionHeader title="طلبات الاعتماد" />
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : (
          <DataTable rows={rows} rowKey={(r) => r.id} empty="لا توجد طلبات." columns={[
            { header: 'المعرف', width: '70px', cell: (r) => <Mono>#{r.id}</Mono> },
            { header: 'العميل', cell: (r) => <Mono>{r.customer_id}</Mono> },
            { header: 'الذمة', cell: (r) => <Mono>{r.due_id ?? '—'}</Mono> },
            { header: 'المبلغ', align: 'end', cell: (r) => <Mono>{formatMoney(r.amount)}</Mono> },
            { header: 'الحالة', align: 'center', cell: (r) => <Pill tone={STATUS[r.status]?.tone ?? 'neutral'}>{STATUS[r.status]?.ar ?? r.status}</Pill> },
            {
              header: '', align: 'end',
              cell: (r) => r.status === 'pending' ? (
                <span className="flex gap-space-sm justify-end">
                  <button className="text-[#ba1a1a] font-small hover:underline" onClick={() => act(() => rejectPayment(r.id, 'مرفوض من المراجعة'), 'رُفض.')} disabled={busy}>رفض</button>
                  <button className="text-primary font-small-medium hover:underline" onClick={() => act(() => approvePayment(r.id), 'اعتُمد.')} disabled={busy}>اعتماد</button>
                </span>
              ) : null,
            },
          ]} />
        )}
      </section>
    </Wide>
  )
}

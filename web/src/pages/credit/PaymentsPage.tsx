import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Card, SectionHeader, Spinner, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import {
  approvePayment, collectPayment, listPayments, openReceipt, rejectPayment, type PaymentApproval,
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

  async function viewReceipt(id: number) {
    try { await openReceipt(id) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر فتح الإيصال') }
  }

  return (
    <Wide>
      <PageTitle title="اعتماد السداد" subtitle="تحصيل يُعتمد بمستوى واحد قبل الشركة — لا يعتمد المحصِّل تحصيله بنفسه." />

      <PageHelp pageKey="payments" />

      <Card className="mt-space-lg flex flex-col gap-space-md">
        <span className="font-headline-2 text-headline-2 text-primary">تسجيل تحصيل جديد</span>
        <form onSubmit={collect} className="flex flex-wrap items-end gap-space-md">
          <div className="w-40"><Field label="رقم العميل" dir="ltr" mono inputMode="numeric" value={cid} onChange={(e) => setCid(e.target.value)} required /></div>
          <div className="w-40"><Field label="رقم الذمة (اختياري)" dir="ltr" mono inputMode="numeric" value={dueId} onChange={(e) => setDueId(e.target.value)} /></div>
          <div className="w-40"><Field label="المبلغ (ج.م)" dir="ltr" mono value={amount} onChange={(e) => setAmount(e.target.value)} required /></div>
          <Button variant="primary" type="submit" disabled={busy || !cid || !amount}>تسجيل تحصيل</Button>
        </form>
      </Card>

      <section className="mt-[48px]">
        <SectionHeader
          title="طلبات الاعتماد"
          action={<Pill tone="warning">{rows.filter((r) => r.status === 'pending').length} معلّق</Pill>}
        />
        <div className="mt-space-md">
          {loading ? <Spinner /> : error ? <InlineError message={error} /> : (
            <Card padded={false} className="overflow-hidden">
              <DataTable rows={rows} rowKey={(r) => r.id} empty="لا توجد طلبات." columns={[
                { header: 'المعرف', width: '70px', cell: (r) => <Mono>#{r.id}</Mono> },
                { header: 'العميل', cell: (r) => <Mono>{r.customer_id}</Mono> },
                { header: 'الذمة', cell: (r) => <Mono>{r.due_id ?? '—'}</Mono> },
                { header: 'المصدر', align: 'center', cell: (r) => r.source === 'customer' ? <Pill tone="signal">تحويل مرفوع</Pill> : <Pill tone="neutral">تحصيل ميداني</Pill> },
                { header: 'المبلغ', align: 'end', cell: (r) => <Mono>{formatMoney(r.amount)}</Mono> },
                { header: 'الحالة', align: 'center', cell: (r) => <Pill tone={STATUS[r.status]?.tone ?? 'neutral'}>{STATUS[r.status]?.ar ?? r.status}</Pill> },
                {
                  header: '', align: 'end',
                  cell: (r) => (
                    <span className="flex gap-space-md justify-end items-center">
                      {r.has_receipt && (
                        <button className="text-primary font-small-medium hover:underline" onClick={() => void viewReceipt(r.id)}>عرض الإيصال</button>
                      )}
                      {r.status === 'pending' && (
                        <>
                          <button className="text-danger font-small-medium hover:underline disabled:opacity-40" onClick={() => act(() => rejectPayment(r.id, 'مرفوض من المراجعة'), 'رُفض.')} disabled={busy}>رفض</button>
                          <button className="text-primary font-small-medium hover:underline disabled:opacity-40" onClick={() => act(() => approvePayment(r.id), 'اعتُمد.')} disabled={busy}>اعتماد</button>
                        </>
                      )}
                    </span>
                  ),
                },
              ]} />
            </Card>
          )}
        </div>
      </section>
    </Wide>
  )
}

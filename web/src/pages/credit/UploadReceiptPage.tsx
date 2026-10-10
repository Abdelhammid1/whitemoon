import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Card, SectionHeader, Spinner, EmptyState } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import { getMyDues, myPayments, openReceipt, uploadReceipt, type MyDue, type PaymentApproval } from '../../api/credit'
import { ApiError } from '../../api/client'
import { formatMoney, formatDate, todayIso } from '../../lib/format'

const selectCls =
  'bg-transparent border-b border-surface-container-high py-2 font-body text-body focus:outline-none focus:border-primary'

const STATUS: Record<string, { ar: string; tone: 'signal' | 'warning' | 'error' | 'neutral' }> = {
  pending: { ar: 'قيد المراجعة', tone: 'warning' },
  approved: { ar: 'معتمد', tone: 'signal' },
  rejected: { ar: 'مرفوض', tone: 'error' },
}

export function UploadReceiptPage() {
  const toast = useToast()
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [amount, setAmount] = useState('')
  const [paidOn, setPaidOn] = useState(todayIso())
  const [dueId, setDueId] = useState('') // '' = دفعة عامة بدون ذمة
  const [busy, setBusy] = useState(false)

  const [rows, setRows] = useState<PaymentApproval[]>([])
  const [dues, setDues] = useState<MyDue[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try { setRows((await myPayments()).items) }
    catch { /* a fresh customer may have none yet */ }
    try { setDues((await getMyDues()).items) }
    catch { /* no open dues */ }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  const selectedDue = dues.find((d) => String(d.id) === dueId) ?? null

  // Picking a due fixes the amount to that due's value — the platform does not
  // accept partial settlement, so the amount must equal the due exactly.
  function pickDue(id: string) {
    setDueId(id)
    const due = dues.find((d) => String(d.id) === id)
    if (due) setAmount(due.amount)
  }

  const remaining = selectedDue ? Number(selectedDue.amount) - Number(amount || 0) : null

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!file) { toast.error('اختر صورة الإيصال أولًا.'); return }
    if (!amount || Number(amount) <= 0) { toast.error('أدخل مبلغًا صحيحًا.'); return }
    if (selectedDue && Number(amount) !== Number(selectedDue.amount)) {
      toast.error('المبلغ يجب أن يساوي قيمة الذمة المختارة (لا يُقبل سداد جزئي).'); return
    }
    setBusy(true)
    try {
      await uploadReceipt({ image: file, amount, paid_on: paidOn, due_id: selectedDue ? selectedDue.id : undefined })
      toast.success('تم إرسال الإيصال، بانتظار مراجعة الموظف.')
      setFile(null); setAmount(''); setPaidOn(todayIso()); setDueId('')
      if (fileRef.current) fileRef.current.value = ''
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر إرسال الإيصال')
    } finally { setBusy(false) }
  }

  async function view(id: number) {
    try { await openReceipt(id) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر فتح الإيصال') }
  }

  return (
    <Narrow>
      <PageTitle title="رفع إيصال تحويل" subtitle="ارفع صورة إيصال التحويل البنكي ليراجعه الموظف" />

      <PageHelp pageKey="upload-receipt" />

      <Card className="mt-space-lg flex flex-col gap-space-md">
        <span className="font-headline-2 text-headline-2 text-primary">إيصال جديد</span>
        <form onSubmit={submit} className="flex flex-col gap-space-md">
          <div className="flex flex-col gap-1">
            <span className="font-small text-small text-secondary">صورة الإيصال</span>
            <input
              id="receipt-file"
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <div className="flex flex-wrap items-center gap-space-sm">
              <Button type="button" onClick={() => fileRef.current?.click()} iconRight="upload">اختر صورة</Button>
              {file ? (
                <span className="font-small text-small text-secondary"><bdi dir="ltr">{file.name}</bdi></span>
              ) : (
                <span className="font-small text-small text-secondary">لم تختر ملفًا بعد</span>
              )}
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <span className="font-small text-small text-secondary">السداد مقابل ذمة</span>
            <select className={selectCls} value={dueId} onChange={(e) => pickDue(e.target.value)}>
              <option value="">دفعة عامة (بدون تحديد ذمة)</option>
              {dues.map((d) => (
                <option key={d.id} value={String(d.id)}>
                  {(d.order_number ? `طلب ${d.order_number} — ` : '') + `${formatMoney(d.amount)} — تستحق ${formatDate(d.due_date)}` + (d.days_overdue > 0 ? ` (متأخرة ${d.days_overdue} يوم)` : '')}
                </option>
              ))}
            </select>
            {dues.length === 0 && (
              <span className="font-small text-small text-secondary">لا توجد ذمم مفتوحة — يمكنك رفع دفعة عامة.</span>
            )}
          </div>
          <div className="flex flex-wrap items-end gap-space-md">
            <div className="w-44">
              <Field label="المبلغ (ج.م)" dir="ltr" mono inputMode="decimal" value={amount}
                onChange={(e) => setAmount(e.target.value)} required disabled={selectedDue != null}
                hint={selectedDue ? 'مثبّت على قيمة الذمة' : undefined} />
            </div>
            <div className="w-44">
              <Field label="تاريخ التحويل" type="date" dir="ltr" mono value={paidOn}
                onChange={(e) => setPaidOn(e.target.value)} />
            </div>
            <Button variant="primary" type="submit" disabled={busy || !file || !amount}>إرسال للمراجعة</Button>
          </div>

          {selectedDue && (
            <div className="rounded-xl bg-surface-container p-space-md flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <span className="font-small text-small text-secondary">المستحق</span>
                <Mono>{formatMoney(selectedDue.amount)}</Mono>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-small text-small text-secondary">المبلغ المُدخل</span>
                <Mono>{formatMoney(amount || '0')}</Mono>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-small text-small text-secondary">الباقي بعد السداد</span>
                <Mono>{formatMoney(String(remaining ?? 0))}</Mono>
              </div>
            </div>
          )}
        </form>
      </Card>

      <section className="mt-[48px]">
        <SectionHeader title="إيصالاتي" />
        <div className="mt-space-md">
          {loading ? <Spinner /> : rows.length === 0 ? (
            <EmptyState title="لم ترفع أي إيصالات بعد" description="ارفع صورة إيصال التحويل البنكي ليظهر هنا بانتظار المراجعة." />
          ) : (
            <Card padded={false} className="overflow-hidden">
              <DataTable rows={rows} rowKey={(r) => r.id} empty="لا توجد إيصالات." columns={[
                { header: 'التاريخ', cell: (r) => <Mono>{formatDate(r.paid_on)}</Mono> },
                { header: 'المبلغ', align: 'end', cell: (r) => <Mono>{formatMoney(r.amount)}</Mono> },
                { header: 'الحالة', align: 'center', cell: (r) => <Pill tone={STATUS[r.status]?.tone ?? 'neutral'}>{STATUS[r.status]?.ar ?? r.status}</Pill> },
                {
                  header: '', align: 'end',
                  cell: (r) => r.has_receipt ? (
                    <button className="text-primary font-small-medium hover:underline" onClick={() => void view(r.id)}>عرض الإيصال</button>
                  ) : null,
                },
              ]} />
            </Card>
          )}
        </div>
      </section>
    </Narrow>
  )
}

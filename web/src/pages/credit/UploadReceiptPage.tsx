import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Card, SectionHeader, Spinner, EmptyState } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import { myPayments, openReceipt, uploadReceipt, type PaymentApproval } from '../../api/credit'
import { ApiError } from '../../api/client'
import { formatMoney, formatDate, todayIso } from '../../lib/format'

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
  const [busy, setBusy] = useState(false)

  const [rows, setRows] = useState<PaymentApproval[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try { setRows((await myPayments()).items) }
    catch { /* a fresh customer may have none yet */ }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!file) { toast.error('اختر صورة الإيصال أولًا.'); return }
    if (!amount || Number(amount) <= 0) { toast.error('أدخل مبلغًا صحيحًا.'); return }
    setBusy(true)
    try {
      await uploadReceipt({ image: file, amount, paid_on: paidOn })
      toast.success('تم إرسال الإيصال، بانتظار مراجعة الموظف.')
      setFile(null); setAmount(''); setPaidOn(todayIso())
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
          <div className="flex flex-wrap items-end gap-space-md">
            <div className="w-44">
              <Field label="المبلغ (ج.م)" dir="ltr" mono inputMode="decimal" value={amount}
                onChange={(e) => setAmount(e.target.value)} required />
            </div>
            <div className="w-44">
              <Field label="تاريخ التحويل" type="date" dir="ltr" mono value={paidOn}
                onChange={(e) => setPaidOn(e.target.value)} />
            </div>
            <Button variant="primary" type="submit" disabled={busy || !file || !amount}>إرسال للمراجعة</Button>
          </div>
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

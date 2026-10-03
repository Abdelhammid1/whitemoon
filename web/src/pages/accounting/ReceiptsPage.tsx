import { useState, type FormEvent } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, SectionHeader, EmptyState } from '../../components/ui'
import { useToast } from '../../components/Toast'
import { resolveReceipt, uploadReceipt } from '../../api/accounting'
import { ApiError } from '../../api/client'

interface Result { receipt_id: number; status: string; ocr_amount: string | null; ocr_reference: string | null }

export function ReceiptsPage() {
  const toast = useToast()
  const [s3Key, setS3Key] = useState('')
  const [expectedAmount, setExpectedAmount] = useState('')
  const [expectedRef, setExpectedRef] = useState('')
  const [stubAmount, setStubAmount] = useState('')
  const [stubRef, setStubRef] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<Result | null>(null)

  async function onUpload(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      const resp = await uploadReceipt({
        image_s3_key: s3Key,
        expected_amount: expectedAmount || undefined,
        expected_reference: expectedRef || undefined,
        ocr_stub_amount: stubAmount || undefined,
        ocr_stub_reference: stubRef || undefined,
      })
      setResult(resp)
      if (resp.status === 'matched') toast.success('تمت المطابقة التلقائية.')
      else toast.info('تم الرفع وتحويله للمراجعة اليدوية.')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الرفع')
    } finally {
      setBusy(false)
    }
  }

  async function resolve(status: 'matched' | 'rejected') {
    if (!result) return
    setBusy(true)
    try {
      const r = await resolveReceipt(result.receipt_id, status)
      setResult({ ...result, status: r.status })
      toast.success(`تم تحديث الحالة إلى ${r.status}.`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الحسم')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Narrow>
      <PageTitle title="الإيصالات والعمليات اليومية" subtitle="مطابقة التحويلات البنكية ضوئيًا (OCR). المتعارض يذهب للمراجعة اليدوية." />

      <form onSubmit={onUpload} className="mt-space-xl flex flex-col gap-space-md">
        <div className="border border-dashed border-surface-container-high rounded-xl p-space-xl text-center">
          <p className="font-body text-body text-secondary">أدخل مسار صورة الإيصال في المخزن (S3)</p>
          <div className="max-w-[420px] mx-auto mt-space-md">
            <Field dir="ltr" mono placeholder="receipts/customer-42/2026-10-10.jpg" value={s3Key} onChange={(e) => setS3Key(e.target.value)} required />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
          <Field label="المبلغ المتوقع (ج.م)" dir="ltr" mono inputMode="decimal" value={expectedAmount} onChange={(e) => setExpectedAmount(e.target.value)} />
          <Field label="الرقم المرجعي المتوقع" dir="ltr" mono value={expectedRef} onChange={(e) => setExpectedRef(e.target.value)} />
        </div>
        <div className="border-t border-surface-container-high pt-space-md">
          <p className="font-small text-small text-secondary mb-space-sm">وضع التطوير — قيم OCR محاكاة</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            <Field label="OCR Amount (stub)" dir="ltr" mono inputMode="decimal" value={stubAmount} onChange={(e) => setStubAmount(e.target.value)} />
            <Field label="OCR Reference (stub)" dir="ltr" mono value={stubRef} onChange={(e) => setStubRef(e.target.value)} />
          </div>
        </div>
        <div className="flex justify-end"><Button variant="primary" type="submit" disabled={busy}>{busy ? 'جار الرفع…' : 'رفع ومطابقة'}</Button></div>
      </form>

      {result && (
        <div className="mt-space-lg flex flex-col gap-space-sm border-t border-surface-container-high pt-space-lg">
          <div className="flex items-center justify-between">
            <span className="font-body text-body text-on-surface">إيصال <bdi dir="ltr" className="font-mono-medium">#{result.receipt_id}</bdi></span>
            <Pill tone={result.status === 'matched' ? 'signal' : result.status === 'rejected' ? 'error' : 'warning'}>{result.status}</Pill>
          </div>
          <span className="font-mono-body text-mono-body text-secondary">
            OCR: <bdi dir="ltr">{result.ocr_amount ?? '—'}</bdi> / <bdi dir="ltr">{result.ocr_reference ?? '—'}</bdi>
          </span>
          {result.status === 'manual_review' && (
            <div className="flex gap-space-sm justify-end">
              <Button variant="destructive" onClick={() => resolve('rejected')} disabled={busy}>رفض</Button>
              <Button variant="primary" onClick={() => resolve('matched')} disabled={busy}>اعتماد كمطابقة</Button>
            </div>
          )}
        </div>
      )}

      <section className="mt-[48px]">
        <SectionHeader title="طابور الإيصالات" />
        <EmptyState title="عرض قائمة الإيصالات قيد الإنشاء" description="الرفع والمطابقة يعملان الآن؛ واجهة سرد الطابور لم تُفعَّل بعد على الخادم." />
      </section>
    </Narrow>
  )
}

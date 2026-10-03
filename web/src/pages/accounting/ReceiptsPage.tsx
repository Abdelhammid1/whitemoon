import { useState, type FormEvent } from 'react'
import { Card, CardHeader } from '../../components/Card'
import { Input } from '../../components/Input'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { resolveReceipt, uploadReceipt } from '../../api/accounting'
import { ApiError } from '../../api/client'
import { useToast } from '../../components/Toast'

interface UploadResult {
  receipt_id: number
  status: string
  ocr_amount: string | null
  ocr_reference: string | null
}

export function ReceiptsPage() {
  const toast = useToast()
  const [s3Key, setS3Key] = useState<string>('')
  const [expectedAmount, setExpectedAmount] = useState<string>('')
  const [expectedRef, setExpectedRef] = useState<string>('')
  const [stubAmount, setStubAmount] = useState<string>('')
  const [stubRef, setStubRef] = useState<string>('')
  const [busy, setBusy] = useState<boolean>(false)
  const [result, setResult] = useState<UploadResult | null>(null)

  async function onUpload(e: FormEvent<HTMLFormElement>) {
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
      else toast.info('تم رفع الإيصال وتحويله لمراجعة يدوية.')
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
      const resp = await resolveReceipt(result.receipt_id, status)
      setResult((prev) => (prev ? { ...prev, status: resp.status } : prev))
      toast.success(`تم تحديث حالة الإيصال إلى ${resp.status}.`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الحسم')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader
          title="إيصالات التحصيل البنكي (OCR)"
          subtitle="US-3.3 — المطابقة التلقائية؛ المتعارض يذهب للمراجعة اليدوية."
        />
        <form onSubmit={onUpload} className="flex flex-col gap-3">
          <Input
            label="مسار S3 لصورة الإيصال"
            dir="ltr"
            placeholder="receipts/customer-42/2026-10-10.jpg"
            value={s3Key}
            onChange={(e) => setS3Key(e.target.value)}
            required
          />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input
              label="المبلغ المتوقع (ج.م)"
              dir="ltr"
              inputMode="decimal"
              value={expectedAmount}
              onChange={(e) => setExpectedAmount(e.target.value)}
            />
            <Input
              label="الرقم المرجعي المتوقع"
              dir="ltr"
              value={expectedRef}
              onChange={(e) => setExpectedRef(e.target.value)}
            />
          </div>
          <div className="rounded-xl border border-warm-mist bg-soft-paper p-3">
            <p className="mb-2 text-body-sm text-graphite">
              وضع التطوير — قيم OCR وهمية (تحاكي استجابة محرك OCR)
            </p>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <Input
                label="OCR Amount (stub)"
                dir="ltr"
                inputMode="decimal"
                value={stubAmount}
                onChange={(e) => setStubAmount(e.target.value)}
              />
              <Input
                label="OCR Reference (stub)"
                dir="ltr"
                value={stubRef}
                onChange={(e) => setStubRef(e.target.value)}
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button variant="filled" type="submit" disabled={busy}>
              {busy ? 'جار الرفع…' : 'رفع ومطابقة'}
            </Button>
          </div>
        </form>
      </Card>

      {result && (
        <Card elevated>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3 text-body text-ink">
              <span>
                المعرّف <code className="font-mono">{result.receipt_id}</code>
              </span>
              <Badge tone={result.status === 'matched' ? 'neutral' : 'muted'}>
                {result.status}
              </Badge>
            </div>
            <div className="text-body-sm text-graphite">
              OCR: <span className="font-mono text-ink">{result.ocr_amount ?? '—'}</span>{' '}
              / <span className="font-mono text-ink">{result.ocr_reference ?? '—'}</span>
            </div>
          </div>
          {result.status === 'manual_review' && (
            <div className="mt-3 flex gap-2 justify-end">
              <Button onClick={() => resolve('rejected')} disabled={busy}>
                رفض
              </Button>
              <Button variant="filled" onClick={() => resolve('matched')} disabled={busy}>
                اعتماد كمطابقة
              </Button>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

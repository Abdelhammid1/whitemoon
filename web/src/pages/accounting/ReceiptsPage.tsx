import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, SectionHeader, Spinner, InlineError, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { Modal } from '../../components/Overlay'
import { fetchReceiptImageUrl, listReceipts, resolveReceipt, uploadReceiptFile, type ReceiptRow } from '../../api/accounting'
import { ApiError } from '../../api/client'
import { PageHelp } from '../../components/PageHelp'
import { formatDate, formatMoney } from '../../lib/format'
import { RECEIPT_STATUS_AR, label } from '../../lib/labels'

interface Result { receipt_id: number; status: string; ocr_amount: string | null; ocr_reference: string | null }

const STATUS_TONE: Record<string, 'signal' | 'warning' | 'error' | 'neutral'> = {
  matched: 'signal',
  manual_review: 'warning',
  rejected: 'error',
}

export function ReceiptsPage() {
  const toast = useToast()
  const [file, setFile] = useState<File | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [expectedAmount, setExpectedAmount] = useState('')
  const [expectedRef, setExpectedRef] = useState('')
  const [stubAmount, setStubAmount] = useState('')
  const [stubRef, setStubRef] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const [rows, setRows] = useState<ReceiptRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [previewId, setPreviewId] = useState<number | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  // Load the receipt image (auth'd blob → object URL) whenever a row is opened,
  // and always revoke the previous object URL to avoid leaking blob handles.
  useEffect(() => {
    if (previewId == null) return
    let url: string | null = null
    let alive = true
    setPreviewLoading(true)
    setPreviewUrl(null)
    void (async () => {
      try {
        url = await fetchReceiptImageUrl(previewId)
        if (alive) setPreviewUrl(url)
        else URL.revokeObjectURL(url)
      } catch (err) {
        if (alive) {
          toast.error(err instanceof ApiError ? err.message : 'تعذّر تحميل الصورة')
          setPreviewId(null)
        }
      } finally {
        if (alive) setPreviewLoading(false)
      }
    })()
    return () => {
      alive = false
      if (url) URL.revokeObjectURL(url)
    }
  }, [previewId]) // eslint-disable-line react-hooks/exhaustive-deps

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await listReceipts()
      setRows(r.items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر تحميل الطابور')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function onUpload(e: FormEvent) {
    e.preventDefault()
    if (!file) {
      toast.error('اختر صورة الإيصال أولًا.')
      return
    }
    setBusy(true)
    try {
      const resp = await uploadReceiptFile(file, {
        expectedAmount: expectedAmount || undefined,
        expectedReference: expectedRef || undefined,
        stubAmount: stubAmount || undefined,
        stubReference: stubRef || undefined,
      })
      setResult({
        receipt_id: resp.receipt_id,
        status: resp.status,
        ocr_amount: resp.ocr_amount,
        ocr_reference: resp.ocr_reference,
      })
      if (resp.status === 'matched') toast.success('تمت المطابقة التلقائية.')
      else toast.info('تم الرفع وتحويله للمراجعة اليدوية.')
      setFile(null)
      await load()
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
      toast.success(`تم تحديث الحالة إلى ${label(RECEIPT_STATUS_AR, r.status)}.`)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الحسم')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Narrow>
      <PageTitle title="الإيصالات والعمليات اليومية" subtitle="مطابقة التحويلات البنكية ضوئيًا (OCR). المتعارض يذهب للمراجعة اليدوية." />

      <PageHelp pageKey="receipts" />

      <Card className="mt-space-xl">
      <form onSubmit={onUpload} className="flex flex-col gap-space-md">
        <div className="border border-dashed border-surface-container-high rounded-xl p-space-xl text-center">
          <p className="font-body text-body text-secondary">ارفع صورة الإيصال (تُخزَّن على الخادم)</p>
          <div className="max-w-[420px] mx-auto mt-space-md flex flex-col items-center gap-space-sm">
            <input
              ref={fileRef}
              type="file"
              accept="image/*,.pdf"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <Button type="button" variant="primary" onClick={() => fileRef.current?.click()} iconRight="upload">اختر ملفًا</Button>
            {file ? (
              <p className="font-small text-small text-secondary">
                <bdi dir="ltr">{file.name}</bdi> — {(file.size / 1024).toFixed(0)} كيلوبايت
              </p>
            ) : (
              <p className="font-small text-small text-secondary">لم تختر ملفًا بعد</p>
            )}
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
          <Field label="المبلغ المتوقع (ج.م)" dir="ltr" mono inputMode="decimal" value={expectedAmount} onChange={(e) => setExpectedAmount(e.target.value)} />
          <Field label="الرقم المرجعي المتوقع" dir="ltr" mono value={expectedRef} onChange={(e) => setExpectedRef(e.target.value)} />
        </div>
        <div className="border-t border-surface-container-high pt-space-md">
          <p className="font-small text-small text-secondary mb-space-sm">وضع التطوير — قيم القراءة الضوئية محاكاة</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            <Field label="مبلغ القراءة الضوئية (محاكاة)" dir="ltr" mono inputMode="decimal" value={stubAmount} onChange={(e) => setStubAmount(e.target.value)} />
            <Field label="مرجع القراءة الضوئية (محاكاة)" dir="ltr" mono value={stubRef} onChange={(e) => setStubRef(e.target.value)} />
          </div>
        </div>
        <div className="flex justify-end"><Button variant="primary" type="submit" disabled={busy}>{busy ? 'جار الرفع…' : 'رفع ومطابقة'}</Button></div>
      </form>
      </Card>

      {result && (
        <Card className="mt-space-lg flex flex-col gap-space-sm">
          <div className="flex items-center justify-between">
            <span className="font-body text-body text-on-surface">إيصال <bdi dir="ltr" className="font-mono-medium">#{result.receipt_id}</bdi></span>
            <Pill tone={STATUS_TONE[result.status] ?? 'warning'}>{label(RECEIPT_STATUS_AR, result.status)}</Pill>
          </div>
          <span className="font-mono-body text-mono-body text-secondary">
            القراءة الضوئية: <bdi dir="ltr">{result.ocr_amount ?? '—'}</bdi> / <bdi dir="ltr">{result.ocr_reference ?? '—'}</bdi>
          </span>
          {result.status === 'manual_review' && (
            <div className="flex gap-space-sm justify-end">
              <Button variant="destructive" onClick={() => resolve('rejected')} disabled={busy}>رفض</Button>
              <Button variant="primary" onClick={() => resolve('matched')} disabled={busy}>اعتماد كمطابقة</Button>
            </div>
          )}
        </Card>
      )}

      <section className="mt-[48px] flex flex-col gap-space-md">
        <SectionHeader title="طابور الإيصالات" />
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : (
          <Card padded={false} className="overflow-hidden">
          <DataTable
            rows={rows}
            rowKey={(r) => r.id}
            onRowClick={(r) => setPreviewId(r.id)}
            empty="لا توجد إيصالات بعد."
            columns={[
              { header: 'المعرف', width: '70px', cell: (r) => <Mono>#{r.id}</Mono> },
              { header: 'الحالة', cell: (r) => <Pill tone={STATUS_TONE[r.status] ?? 'neutral'}>{label(RECEIPT_STATUS_AR, r.status)}</Pill> },
              { header: 'مبلغ القراءة', align: 'end', cell: (r) => <Mono>{r.ocr_amount ? formatMoney(r.ocr_amount) : '—'}</Mono> },
              { header: 'مرجع القراءة', cell: (r) => <Mono>{r.ocr_reference ?? '—'}</Mono> },
              { header: 'طلب مطابق', align: 'center', cell: (r) => <Mono>{r.matched_order_id ?? '—'}</Mono> },
              { header: 'رُفع', align: 'end', cell: (r) => <Mono>{r.uploaded_at ? formatDate(r.uploaded_at) : '—'}</Mono> },
            ]}
          />
          </Card>
        )}
      </section>

      <Modal
        open={previewId != null}
        onClose={() => setPreviewId(null)}
        title={previewId != null ? `صورة الإيصال #${previewId}` : 'صورة الإيصال'}
      >
        <div className="flex items-center justify-center min-h-[200px]">
          {previewLoading ? (
            <Spinner />
          ) : previewUrl ? (
            <img src={previewUrl} alt="صورة الإيصال" className="max-h-[60vh] w-auto rounded-lg" />
          ) : (
            <p className="font-body text-body text-secondary">لا توجد صورة.</p>
          )}
        </div>
      </Modal>
    </Narrow>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, EmptyState, InlineError, Button, Field, SectionHeader } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import { getRfq, listRfqOffers, submitRfqOffer, type Rfq, type RfqOffer } from '../../api/commerce'
import { ApiError } from '../../api/client'
import { formatDate, formatMoney } from '../../lib/format'

export function RfqDetailPage() {
  const { id } = useParams()
  const toast = useToast()
  const { user } = useAuth()
  const isSupplier = user?.kind === 'supplier'
  const [rfq, setRfq] = useState<Rfq | null>(null)
  const [offers, setOffers] = useState<RfqOffer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [unitPrice, setUnitPrice] = useState('')
  const [moq, setMoq] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [r, o] = await Promise.all([getRfq(Number(id)), listRfqOffers(Number(id))])
      setRfq(r)
      setOffers(o.items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { void load() }, [load])

  async function submitOffer(e: React.FormEvent) {
    e.preventDefault()
    if (!unitPrice || !moq) { toast.error('أدخل سعر الوحدة وأدنى كمية.'); return }
    setSubmitting(true)
    try {
      await submitRfqOffer(Number(id), unitPrice, moq)
      toast.success('تم إرسال عرضك.')
      setUnitPrice('')
      setMoq('')
      const o = await listRfqOffers(Number(id))
      setOffers(o.items)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر إرسال العرض')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error || !rfq) return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>

  return (
    <Narrow>
      <PageTitle title={`طلب عرض ${rfq.number}`} subtitle="العروض معروضة بالسعر فقط — دون كشف هوية المورد." />
      <div className="mt-space-sm flex flex-wrap items-center gap-space-sm">
        <Pill tone={rfq.status === 'open' ? 'signal' : 'neutral'}>{rfq.status === 'open' ? 'مفتوح' : rfq.status}</Pill>
        <span className="font-body text-body text-secondary">المنتج <Mono>#{rfq.product_id}</Mono> — كمية <Mono>{rfq.qty}</Mono></span>
        {rfq.deadline && <span className="font-mono-body text-mono-body text-secondary">حتى {formatDate(rfq.deadline)}</span>}
      </div>

      <div className="mt-space-xl">
        {offers.length === 0 ? (
          <EmptyState title="لم تصل عروض بعد." />
        ) : (
          <DataTable
            rows={offers}
            rowKey={(o) => o.offer_id}
            columns={[
              { header: 'العرض', cell: (o) => <Mono>عرض #{o.offer_id}</Mono> },
              { header: 'سعر الوحدة', align: 'end', cell: (o) => <Mono>{formatMoney(o.unit_price)}</Mono> },
              { header: 'أدنى كمية', align: 'end', cell: (o) => <Mono>{o.moq}</Mono> },
              { header: 'التاريخ', align: 'end', cell: (o) => <Mono>{formatDate(o.submitted_at)}</Mono> },
            ]}
          />
        )}
      </div>

      {isSupplier && rfq.status === 'open' && (
        <form onSubmit={submitOffer} className="mt-space-xl flex flex-col gap-space-md">
          <SectionHeader title="تقديم عرض" />
          <p className="font-small text-small text-secondary">
            عرضك يُعرض على العميل بالسعر فقط — دون كشف هويتك.
          </p>
          <div className="flex flex-wrap items-end gap-space-md">
            <div className="w-48">
              <Field
                label="سعر الوحدة (ج.م)"
                dir="ltr"
                mono
                inputMode="decimal"
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
              />
            </div>
            <div className="w-40">
              <Field
                label="أدنى كمية"
                dir="ltr"
                mono
                inputMode="numeric"
                value={moq}
                onChange={(e) => setMoq(e.target.value)}
              />
            </div>
            <Button type="submit" variant="primary" disabled={submitting} iconRight="send">
              إرسال العرض
            </Button>
          </div>
        </form>
      )}
    </Narrow>
  )
}

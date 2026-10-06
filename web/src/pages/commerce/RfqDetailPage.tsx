import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, EmptyState, InlineError, Button, Field, SectionHeader, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import { getRfq, listRfqOffers, submitRfqOffer, type Rfq, type RfqOffer } from '../../api/commerce'
import { ApiError } from '../../api/client'
import { formatDate, formatMoney, formatNumber } from '../../lib/format'
import { PageHelp } from '../../components/PageHelp'

const STATUS_AR: Record<string, string> = { open: 'مفتوح', closed: 'مغلق', awarded: 'تم الترسية', cancelled: 'ملغى' }

export function RfqDetailPage() {
  const { id } = useParams()
  const toast = useToast()
  const { user } = useAuth()
  const isSupplier = user?.kind === 'supplier'
  const isAdmin = user?.kind === 'admin' || user?.kind === 'staff'
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
      const r = await getRfq(Number(id))
      setRfq(r)
      if (r.my_offer) {
        setUnitPrice(r.my_offer.unit_price)
        setMoq(r.my_offer.moq)
      }
      // A supplier never sees competitors' offers — only the initiator/admin compares.
      if (!isSupplier) {
        const o = await listRfqOffers(Number(id))
        setOffers(o.items)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }, [id, isSupplier])

  useEffect(() => { void load() }, [load])

  async function submitOffer(e: React.FormEvent) {
    e.preventDefault()
    if (!unitPrice || !moq) { toast.error('أدخل سعر الوحدة والحد الأدنى للكمية.'); return }
    setSubmitting(true)
    try {
      await submitRfqOffer(Number(id), unitPrice, moq)
      toast.success(rfq?.my_offer ? 'تم تحديث عرضك.' : 'تم إرسال عرضك.')
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر إرسال العرض')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error || !rfq) return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>

  // Comparison: cheapest first; the lowest unit price is the best offer.
  const sorted = [...offers].sort((a, b) => Number(a.unit_price) - Number(b.unit_price))
  const bestId = sorted[0]?.offer_id ?? null

  return (
    <Narrow>
      <PageTitle
        title={`طلب عرض ${rfq.number}`}
        subtitle={isSupplier ? 'قدّم سعرك — يُعرض على العميل دون كشف هويتك.' : 'العروض معروضة بالسعر فقط — دون كشف هوية المورد.'}
      />
      <PageHelp pageKey="rfq-detail" />

      <Card className="mt-space-md flex flex-wrap items-center gap-space-md">
        <Pill tone={rfq.status === 'open' ? 'signal' : rfq.status === 'cancelled' ? 'error' : 'neutral'}>
          {STATUS_AR[rfq.status] ?? rfq.status}
        </Pill>
        <span className="font-body text-body text-secondary">
          الصنف {rfq.product_name ? <span className="text-on-surface">{rfq.product_name}</span> : <Mono>#{rfq.product_id}</Mono>} — كمية <Mono>{formatNumber(rfq.qty)}</Mono>
        </span>
        {rfq.deadline && <span className="font-mono-body text-mono-body text-secondary">حتى {formatDate(rfq.deadline)}</span>}
        {rfq.qualification_requirements && (
          <span className="font-small text-small text-secondary">المتطلبات: {rfq.qualification_requirements}</span>
        )}
      </Card>

      {/* Supplier: submit / update their own offer. Never the comparison. */}
      {isSupplier ? (
        rfq.status === 'open' ? (
          <Card className="mt-space-xl flex flex-col gap-space-md">
            <SectionHeader title={rfq.my_offer ? 'تحديث عرضك' : 'تقديم عرض'} />
            <p className="font-small text-small text-secondary">عرضك يُعرض على العميل بالسعر فقط — دون كشف هويتك.</p>
            <form onSubmit={submitOffer} className="flex flex-wrap items-end gap-space-md">
              <div className="w-48">
                <Field label="سعر الوحدة (ج.م)" dir="ltr" mono inputMode="decimal" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} />
              </div>
              <div className="w-40">
                <Field label="الحد الأدنى للكمية" dir="ltr" mono inputMode="numeric" value={moq} onChange={(e) => setMoq(e.target.value)} />
              </div>
              <Button type="submit" variant="primary" disabled={submitting} iconRight="send">
                {rfq.my_offer ? 'تحديث العرض' : 'إرسال العرض'}
              </Button>
            </form>
          </Card>
        ) : (
          <div className="mt-space-xl"><EmptyState title="هذا الطلب لم يعد مفتوحًا لاستقبال العروض." /></div>
        )
      ) : (
        <section className="mt-space-xl">
          <SectionHeader title="مقارنة العروض" />
          <div className="mt-space-md">
            {sorted.length === 0 ? (
              <EmptyState title="لا توجد عروض بعد." />
            ) : (
              <Card padded={false} className="overflow-hidden">
                <DataTable
                  rows={sorted}
                  rowKey={(o) => o.offer_id}
                  columns={[
                    {
                      header: 'العرض',
                      cell: (o) => (
                        <span className="flex items-center gap-space-sm">
                          <Mono>عرض #{o.offer_id}</Mono>
                          {o.offer_id === bestId && <Pill tone="signal">الأفضل سعرًا</Pill>}
                          {isAdmin && o.supplier_id != null && <Mono>مورد #{o.supplier_id}</Mono>}
                        </span>
                      ),
                    },
                    { header: 'السعر', align: 'end', cell: (o) => <Mono>{formatMoney(o.unit_price)}</Mono> },
                    { header: 'الحد الأدنى', align: 'end', cell: (o) => <Mono>{formatNumber(o.moq)}</Mono> },
                    { header: 'تاريخ العرض', align: 'end', cell: (o) => <Mono>{formatDate(o.submitted_at)}</Mono> },
                  ]}
                />
              </Card>
            )}
          </div>
        </section>
      )}
    </Narrow>
  )
}

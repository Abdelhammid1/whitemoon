import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Card, Pill, Spinner, EmptyState, InlineError, SectionHeader } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import { createRfq, listRfqs, type Rfq } from '../../api/commerce'
import { ApiError } from '../../api/client'
import { PageHelp } from '../../components/PageHelp'
import { formatDate, formatMoney, formatNumber } from '../../lib/format'

type Tone = 'signal' | 'neutral' | 'warning' | 'error'
const STATUS_AR: Record<string, string> = { open: 'مفتوح', closed: 'مغلق', awarded: 'تم الترسية', cancelled: 'ملغى' }
const STATUS_TONE: Record<string, Tone> = { open: 'signal', closed: 'neutral', awarded: 'neutral', cancelled: 'error' }

export function RfqPage() {
  const { user } = useAuth()
  const isSupplier = user?.kind === 'supplier'

  const toast = useToast()
  const navigate = useNavigate()
  const [rows, setRows] = useState<Rfq[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setRows((await listRfqs()).items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => { void load() }, [load])

  // ---- customer: create a new RFQ ----
  const [productId, setProductId] = useState('')
  const [qty, setQty] = useState('')
  const [deadline, setDeadline] = useState('')
  const [reqs, setReqs] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      const rfq = await createRfq({
        product_id: Number(productId),
        qty,
        deadline: deadline || undefined,
        qualification_requirements: reqs || undefined,
      })
      toast.success(`تم إنشاء طلب العرض ${rfq.number}.`)
      navigate(`/rfq/${rfq.id}`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر الإنشاء')
    } finally {
      setBusy(false)
    }
  }

  const title = isSupplier ? 'طلبات عروض الأسعار الواردة' : 'طلبات عرض السعر (RFQ)'
  const subtitle = isSupplier
    ? 'طلبات مفتوحة من عملاء — الشركة تتوسّط، وهوية العميل تبقى مخفية عنك.'
    : 'الشركة تتوسّط العروض — هوية الموردين تبقى مخفية عنك.'

  return (
    <Narrow>
      <PageTitle title={title} subtitle={subtitle} />
      <PageHelp pageKey="rfq" />

      {/* Customer-only: create a new RFQ */}
      {!isSupplier && user?.kind === 'customer' && (
        <Card className="mt-space-xl max-w-[480px]">
          <SectionHeader title="طلب عرض جديد" />
          <form onSubmit={submit} className="mt-space-md flex flex-col gap-space-md">
            <Field label="رقم المنتج" dir="ltr" mono inputMode="numeric" value={productId} onChange={(e) => setProductId(e.target.value)} required />
            <Field label="الكمية المطلوبة" dir="ltr" mono inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} required />
            <Field label="آخر موعد (اختياري)" type="date" dir="ltr" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
            <Field label="متطلبات التأهيل (اختياري)" value={reqs} onChange={(e) => setReqs(e.target.value)} />
            <div className="flex justify-end pt-space-xs">
              <Button variant="primary" type="submit" disabled={busy || !productId || !qty}>إرسال الطلب</Button>
            </div>
          </form>
        </Card>
      )}

      <section className="mt-space-xl">
        <SectionHeader title={isSupplier ? 'الطلبات المفتوحة' : 'طلباتي'} />
        <div className="mt-space-md">
          {loading ? (
            <Spinner />
          ) : error ? (
            <InlineError message={error} />
          ) : rows.length === 0 ? (
            <EmptyState title={isSupplier ? 'لا توجد طلبات مفتوحة حاليًا.' : 'لا توجد طلبات بعد — أنشئ طلب عرض من الأعلى.'} />
          ) : (
            <Card padded={false} className="overflow-hidden">
              <DataTable
                rows={rows}
                rowKey={(r) => r.id}
                onRowClick={(r) => navigate(`/rfq/${r.id}`)}
                columns={[
                  { header: 'رقم الطلب', cell: (r) => <Mono>{r.number}</Mono> },
                  { header: 'الصنف', cell: (r) => r.product_name ?? <Mono>#{r.product_id}</Mono> },
                  { header: 'الكمية', align: 'end', cell: (r) => <Mono>{formatNumber(r.qty)}</Mono> },
                  { header: 'آخر موعد', align: 'end', cell: (r) => <Mono>{r.deadline ? formatDate(r.deadline) : '—'}</Mono> },
                  { header: 'العروض', align: 'end', cell: (r) => <Mono>{formatNumber(r.offer_count)}</Mono> },
                  ...(isSupplier
                    ? [{
                        header: 'عرضي',
                        align: 'end' as const,
                        cell: (r: Rfq) =>
                          r.my_offer ? (
                            <Pill tone="signal">قدّمت عرضًا — {formatMoney(r.my_offer.unit_price)}</Pill>
                          ) : (
                            <Button onClick={() => navigate(`/rfq/${r.id}`)} iconRight="send">تقديم عرض</Button>
                          ),
                      }]
                    : [{
                        header: 'الحالة',
                        align: 'end' as const,
                        cell: (r: Rfq) => <Pill tone={STATUS_TONE[r.status] ?? 'neutral'}>{STATUS_AR[r.status] ?? r.status}</Pill>,
                      }]),
                ]}
              />
            </Card>
          )}
        </div>
      </section>
    </Narrow>
  )
}

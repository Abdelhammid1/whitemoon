import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Pill, Button, Spinner, InlineError, SectionHeader, EmptyState } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { getOrder, type Order } from '../../api/commerce'
import { availableSlots, bookSlot, trackShipment, type Shipment, type Slot } from '../../api/logistics'
import { ApiError } from '../../api/client'
import { formatDate, formatMoney, todayIso } from '../../lib/format'

const STATUS_AR: Record<string, string> = {
  pending: 'قيد الانتظار', confirmed: 'مؤكد', fulfilled: 'منفَّذ', cancelled: 'ملغى',
}

function plusDaysIso(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

export function OrderDetailPage() {
  const { id } = useParams()
  const oid = Number(id)
  const toast = useToast()
  const [order, setOrder] = useState<Order | null>(null)
  const [shipment, setShipment] = useState<Shipment | null>(null)
  const [slots, setSlots] = useState<Slot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [booking, setBooking] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const o = await getOrder(oid)
      setOrder(o)
      // Shipment may not exist yet (404) — then the customer can book a slot.
      let sh: Shipment | null = null
      try { sh = await trackShipment(oid) } catch (err) {
        if (!(err instanceof ApiError && err.status === 404)) throw err
      }
      setShipment(sh)
      if (sh === null && o.status !== 'cancelled') {
        const { items } = await availableSlots(todayIso(), plusDaysIso(14))
        setSlots(items)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }, [oid])
  useEffect(() => { void load() }, [load])

  async function book(slotId: number) {
    setBooking(true)
    try {
      const sh = await bookSlot(oid, slotId)
      setShipment(sh)
      toast.success('تم حجز موعد التسليم.')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر الحجز')
    } finally {
      setBooking(false)
    }
  }

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error || !order) return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>

  return (
    <Narrow>
      <PageTitle title={`طلب ${order.number}`} />
      <div className="mt-space-sm flex items-center gap-space-sm">
        <Pill tone={order.status === 'cancelled' ? 'error' : order.status === 'pending' ? 'warning' : 'signal'}>
          {STATUS_AR[order.status] ?? order.status}
        </Pill>
        <span className="font-body text-body text-secondary">{order.payment_mode === 'deferred' ? 'آجل' : 'نقدي'}</span>
        <span className="font-mono-body text-mono-body text-secondary">{formatDate(order.placed_at)}</span>
      </div>

      <div className="mt-space-xl">
        <DataTable
          rows={order.lines ?? []}
          rowKey={(l) => `${l.product_id}`}
          empty="لا توجد بنود."
          columns={[
            { header: 'المنتج', cell: (l) => <Mono>#{l.product_id}</Mono> },
            { header: 'الكمية', align: 'end', cell: (l) => <Mono>{l.qty}</Mono> },
            { header: 'سعر الوحدة', align: 'end', cell: (l) => <Mono>{formatMoney(l.unit_price)}</Mono> },
            { header: 'الإجمالي', align: 'end', cell: (l) => <Mono>{formatMoney(l.line_total)}</Mono> },
          ]}
        />
      </div>

      <div className="mt-space-lg flex items-center justify-between border-t border-surface-container-high pt-space-md">
        <span className="font-body-medium text-body-medium">الإجمالي</span>
        <span className="font-display text-headline-1 text-primary">
          <Mono>{formatMoney(order.payment_mode === 'deferred' ? order.total_deferred : order.total_cash)}</Mono> ج.م
        </span>
      </div>

      {/* Delivery: track an existing shipment, or book a slot. */}
      <section className="mt-[48px]">
        <SectionHeader title="التسليم" />
        {shipment ? (
          <div className="mt-space-md flex flex-col gap-space-md">
            <div className="flex items-center gap-space-sm">
              <Pill tone={shipment.status === 'delivered' ? 'signal' : shipment.status === 'failed' ? 'error' : 'warning'}>
                {shipment.status === 'delivered' ? 'تم التسليم' : shipment.status === 'failed' ? 'فشل التسليم' : 'جارٍ التنفيذ'}
              </Pill>
              <Link to={`/orders/${order.id}/shipment`} className="font-body text-body text-primary hover:underline">
                تتبع الشحنة ↗
              </Link>
            </div>
            {shipment.confirmation_code && (
              <div className="p-space-md bg-surface-container-low rounded-xl flex items-center justify-between gap-space-md">
                <span className="font-small text-small text-secondary">سلّم هذا الرمز للمندوب عند الاستلام</span>
                <span className="font-mono-medium text-headline-1 tracking-[0.2em] text-primary" dir="ltr">{shipment.confirmation_code}</span>
              </div>
            )}
          </div>
        ) : order.status === 'cancelled' ? (
          <div className="mt-space-md"><EmptyState title="الطلب ملغى — لا يوجد تسليم." /></div>
        ) : slots.length === 0 ? (
          <div className="mt-space-md"><EmptyState title="لا توجد مواعيد تسليم متاحة حالياً." description="تُضاف المواعيد من قسم اللوجستيات. حاول لاحقاً." /></div>
        ) : (
          <div className="mt-space-md flex flex-col gap-space-sm">
            <p className="font-small text-small text-secondary">اختر موعد التسليم المناسب خلال الأيام القادمة:</p>
            <div className="flex flex-col divide-y divide-surface-container">
              {slots.map((s) => (
                <div key={s.id} className="flex items-center justify-between py-space-sm gap-space-md">
                  <div className="flex items-center gap-space-md min-w-0">
                    <Icon name="event" size={18} className="text-secondary shrink-0" />
                    <div className="flex flex-col min-w-0">
                      <span className="font-body-medium text-body-medium text-primary"><Mono>{s.slot_date}</Mono> — {s.window}</span>
                      <span className="font-small text-small text-secondary">المتبقي <Mono>{s.remaining}</Mono> من <Mono>{s.capacity}</Mono></span>
                    </div>
                  </div>
                  <Button variant="primary" disabled={booking || s.remaining <= 0} onClick={() => void book(s.id)}>احجز</Button>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
    </Narrow>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Pill, Button, Spinner, InlineError, SectionHeader, EmptyState, Card } from '../../components/ui'
import { Modal } from '../../components/Overlay'
import { Icon } from '../../components/Icon'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import {
  getOrder,
  confirmOrder,
  fulfillOrder,
  cancelOrder,
  openOrderInvoice,
  type Order,
  type OrderAction,
} from '../../api/commerce'
import { availableSlots, bookSlot, trackShipment, type Shipment, type Slot } from '../../api/logistics'
import { ApiError } from '../../api/client'
import { formatDate, formatMoney, todayIso } from '../../lib/format'
import { PageHelp } from '../../components/PageHelp'

const STATUS_AR: Record<string, string> = {
  pending: 'قيد الانتظار', confirmed: 'مؤكد', fulfilled: 'منفَّذ', cancelled: 'ملغى',
}

function plusDaysIso(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

const ACTION_DONE: Record<OrderAction, string> = {
  confirm: 'تم تأكيد الطلب.',
  fulfill: 'تم تجهيز الطلب.',
  cancel: 'تم إلغاء الطلب.',
}

export function OrderDetailPage() {
  const { id } = useParams()
  const oid = Number(id)
  const toast = useToast()
  const { user } = useAuth()
  const isStaff = user?.kind === 'admin' || user?.kind === 'staff'
  const [order, setOrder] = useState<Order | null>(null)
  const [shipment, setShipment] = useState<Shipment | null>(null)
  const [slots, setSlots] = useState<Slot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [booking, setBooking] = useState(false)
  const [acting, setActing] = useState(false)
  const [bookOpen, setBookOpen] = useState(false)

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
      setBookOpen(false)
      toast.success('تم حجز موعد التسليم.')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر الحجز')
    } finally {
      setBooking(false)
    }
  }

  async function openInvoice() {
    try {
      await openOrderInvoice(oid)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر فتح الفاتورة')
    }
  }

  async function doTransition(action: OrderAction) {
    setActing(true)
    try {
      if (action === 'confirm') await confirmOrder(oid)
      else if (action === 'fulfill') await fulfillOrder(oid)
      else await cancelOrder(oid)
      toast.success(ACTION_DONE[action])
      await load()
    } catch (err) {
      // Invalid transitions surface as a 409 with an Arabic message.
      toast.error(err instanceof ApiError ? err.message : 'تعذّر تنفيذ العملية')
    } finally {
      setActing(false)
    }
  }

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error || !order) return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>

  // Admin/staff get the per-supplier breakdown (sub_orders); customers get flat lines.
  const subOrders = order.sub_orders ?? null
  const lineCount = order.lines?.length ?? subOrders?.reduce((n, s) => n + s.lines.length, 0) ?? 0
  const canConfirm = order.status === 'pending'
  const canFulfill = order.status === 'confirmed'
  const canCancel = order.status === 'pending' || order.status === 'confirmed'
  const canBook = !shipment && order.status !== 'cancelled'
  const showActions = isStaff && (canConfirm || canFulfill || canCancel || canBook)

  return (
    <Narrow>
      <PageTitle title={`طلب ${order.number}`} />
      <PageHelp pageKey="order-detail" />
      <div className="mt-space-sm flex flex-wrap items-center gap-space-sm">
        <Pill tone={order.status === 'cancelled' ? 'error' : order.status === 'pending' ? 'warning' : 'signal'}>
          {STATUS_AR[order.status] ?? order.status}
        </Pill>
        <span className="font-body text-body text-secondary">{order.payment_mode === 'deferred' ? 'آجل' : 'نقدي'}</span>
        <span className="font-mono-body text-mono-body text-secondary">{formatDate(order.placed_at)}</span>
        <Button className="ms-auto" iconRight="picture_as_pdf" onClick={() => void openInvoice()}>
          فاتورة PDF
        </Button>
      </div>

      {/* Admin/staff actions — only the valid transitions for the current status. */}
      {showActions && (
        <Card className="mt-space-lg flex flex-wrap items-center gap-space-sm">
          {canConfirm && (
            <Button variant="primary" disabled={acting} onClick={() => void doTransition('confirm')}>
              تأكيد الطلب
            </Button>
          )}
          {canFulfill && (
            <Button variant="primary" disabled={acting} onClick={() => void doTransition('fulfill')}>
              تجهيز الطلب
            </Button>
          )}
          {canBook && (
            <Button disabled={acting} onClick={() => setBookOpen(true)} iconRight="local_shipping">
              حجز شحنة
            </Button>
          )}
          {canCancel && (
            <Button variant="destructive" disabled={acting} onClick={() => void doTransition('cancel')}>
              إلغاء
            </Button>
          )}
        </Card>
      )}

      {/* Order KPI tiles */}
      <section className="mt-space-xl grid grid-cols-1 sm:grid-cols-3 gap-space-md">
        <Card className="flex flex-col gap-space-xs">
          <span className="font-small text-small text-secondary">الإجمالي</span>
          <div className="flex items-baseline gap-space-xs" dir="ltr">
            <span className="font-mono-medium text-display text-primary tracking-tight">
              {formatMoney(order.payment_mode === 'deferred' ? order.total_deferred : order.total_cash)}
            </span>
            <span className="font-small text-small text-secondary">ج.م</span>
          </div>
        </Card>
        <Card className="flex flex-col gap-space-xs">
          <span className="font-small text-small text-secondary">طريقة الدفع</span>
          <span className="font-body-medium text-body-medium text-on-surface">
            {order.payment_mode === 'deferred' ? 'بيع آجل' : 'نقدي فوري'}
          </span>
        </Card>
        <Card className="flex flex-col gap-space-xs">
          <span className="font-small text-small text-secondary">عدد البنود</span>
          <Mono className="text-display text-primary tracking-tight">{lineCount}</Mono>
        </Card>
      </section>

      <section className="mt-space-xl">
        <SectionHeader title="بنود الطلب" />
        {subOrders ? (
          // Admin/staff: per-supplier breakdown (supplier identity stays admin-only).
          <div className="mt-space-md flex flex-col gap-space-md">
            {subOrders.map((s) => (
              <Card key={s.id} padded={false} className="overflow-hidden">
                <div className="flex items-center justify-between gap-space-md px-space-lg py-space-md border-b border-surface-container-high">
                  <span className="font-body-medium text-body-medium text-on-surface">
                    مورّد <Mono>#{s.supplier_id}</Mono>
                  </span>
                  <span className="font-small text-small text-secondary">
                    الإجمالي الفرعي <Mono>{formatMoney(s.subtotal)}</Mono>
                  </span>
                </div>
                <DataTable
                  rows={s.lines}
                  rowKey={(l) => `${s.id}-${l.product_id}`}
                  empty="لا توجد بنود."
                  columns={[
                    { header: 'المنتج', cell: (l) => <Mono>#{l.product_id}</Mono> },
                    { header: 'الكمية', align: 'end', cell: (l) => <Mono>{l.qty}</Mono> },
                    { header: 'سعر الوحدة', align: 'end', cell: (l) => <Mono>{formatMoney(l.unit_price)}</Mono> },
                    { header: 'الإجمالي', align: 'end', cell: (l) => <Mono>{formatMoney(l.line_total)}</Mono> },
                  ]}
                />
              </Card>
            ))}
          </div>
        ) : (
          <Card padded={false} className="mt-space-md overflow-hidden">
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
          </Card>
        )}
      </section>

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
        ) : isStaff ? (
          <div className="mt-space-md"><EmptyState title="لم يُحجز موعد تسليم بعد." description="استخدم «حجز شحنة» بالأعلى لإسناد موعد." /></div>
        ) : slots.length === 0 ? (
          <div className="mt-space-md"><EmptyState title="لا توجد مواعيد تسليم متاحة حالياً." description="تُضاف المواعيد من قسم اللوجستيات. حاول لاحقاً." /></div>
        ) : (
          <div className="mt-space-md flex flex-col gap-space-sm">
            <p className="font-small text-small text-secondary">اختر موعد التسليم المناسب خلال الأيام القادمة:</p>
            <Card padded={false} className="px-space-lg flex flex-col divide-y divide-surface-container">
              {slots.map((s) => (
                <div key={s.id} className="flex items-center justify-between py-space-md gap-space-md">
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
            </Card>
          </div>
        )}
      </section>

      {/* Admin/staff slot booking */}
      <Modal open={bookOpen} onClose={() => setBookOpen(false)} title="حجز شحنة">
        {slots.length === 0 ? (
          <EmptyState title="لا توجد مواعيد تسليم متاحة حالياً." description="تُضاف المواعيد من قسم اللوجستيات." />
        ) : (
          <div className="flex flex-col gap-space-sm">
            <p className="font-small text-small text-secondary">اختر موعد التسليم المناسب خلال الأيام القادمة:</p>
            <div className="flex flex-col divide-y divide-surface-container-high">
              {slots.map((s) => (
                <div key={s.id} className="flex items-center justify-between py-space-md gap-space-md">
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
      </Modal>
    </Narrow>
  )
}

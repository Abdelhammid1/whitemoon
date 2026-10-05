import { useState } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, SectionHeader, EmptyState, Card } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { confirmDelivery, trackShipment, updateShipmentLocation, type Shipment } from '../../api/logistics'
import { ApiError } from '../../api/client'

const STATUS_AR: Record<string, string> = {
  scheduled: 'مجدول', shipped: 'تم الشحن', in_transit: 'في الطريق', delivered: 'تم التسليم', failed: 'فشل التسليم',
}

interface ShortageRow { product_id: string; qty: string; note: string }

export function DeliveryConfirmPage() {
  const toast = useToast()
  const [orderId, setOrderId] = useState('')
  const [shipment, setShipment] = useState<Shipment | null>(null)
  const [method, setMethod] = useState<'code' | 'signature'>('code')
  const [code, setCode] = useState('')
  const [signature, setSignature] = useState('')
  const [shortages, setShortages] = useState<ShortageRow[]>([])
  const [busy, setBusy] = useState(false)

  async function lookup() {
    setBusy(true); setShipment(null)
    try {
      setShipment(await trackShipment(Number(orderId)))
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) toast.error('لا توجد شحنة لهذا الطلب.')
      else toast.error(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setBusy(false)
    }
  }

  function addShortage() { setShortages([...shortages, { product_id: '', qty: '', note: '' }]) }
  function setShortage(i: number, patch: Partial<ShortageRow>) {
    setShortages(shortages.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))
  }
  function removeShortage(i: number) { setShortages(shortages.filter((_, idx) => idx !== i)) }

  async function submit() {
    if (!shipment) return
    setBusy(true)
    try {
      const lines = shortages
        .filter((r) => Number(r.product_id) > 0 && Number(r.qty) > 0)
        .map((r) => ({ product_id: Number(r.product_id), qty: Number(r.qty), note: r.note || undefined }))
      const s = await confirmDelivery(shipment.id, {
        confirmation_code: method === 'code' ? code.trim() : undefined,
        signature: method === 'signature' ? signature.trim() : undefined,
        shortages: lines,
      })
      setShipment(s)
      toast.success('تم تأكيد التسليم.')
      setCode(''); setSignature(''); setShortages([])
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر تأكيد التسليم')
    } finally {
      setBusy(false)
    }
  }

  function updateLocation() {
    if (!shipment) return
    if (!('geolocation' in navigator)) {
      toast.error('تحديد الموقع غير مدعوم على هذا الجهاز.')
      return
    }
    setBusy(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        void (async () => {
          try {
            await updateShipmentLocation(shipment.id, pos.coords.latitude, pos.coords.longitude)
            setShipment(await trackShipment(shipment.order_id))
            toast.success('تم تحديث موقع الشحنة.')
          } catch (err) {
            toast.error(err instanceof ApiError ? err.message : 'تعذّر تحديث الموقع')
          } finally {
            setBusy(false)
          }
        })()
      },
      (err) => {
        setBusy(false)
        toast.error(
          err.code === err.PERMISSION_DENIED
            ? 'تم رفض إذن الوصول إلى الموقع.'
            : 'تعذّر قراءة الموقع الحالي.',
        )
      },
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  const canSubmit = !busy && !!shipment && shipment.status !== 'delivered' &&
    (method === 'code' ? code.trim().length > 0 : signature.trim().length > 0)

  return (
    <Narrow>
      <PageTitle title="تأكيد التسليم" subtitle="للمندوب — أكّد تسليم الشحنة برمز العميل أو بالتوقيع، وسجّل أي نواقص." />

      {/* Lookup */}
      <Card className="mt-space-xl flex items-end gap-space-sm">
        <div className="w-48"><Field label="رقم الطلب" dir="ltr" mono value={orderId} inputMode="numeric" onChange={(e) => setOrderId(e.target.value)} /></div>
        <Button variant="primary" disabled={busy || !orderId} onClick={() => void lookup()}>استدعاء الشحنة</Button>
      </Card>

      {shipment && (
        <>
          <Card className="mt-space-lg flex flex-wrap items-center gap-space-sm">
            <Mono className="text-secondary">#{shipment.order_id}</Mono>
            <Pill tone={shipment.status === 'delivered' ? 'signal' : shipment.status === 'failed' ? 'error' : 'warning'}>
              {STATUS_AR[shipment.status] ?? shipment.status}
            </Pill>
            {shipment.status !== 'delivered' && (
              <Button className="ms-auto" disabled={busy} onClick={() => updateLocation()} iconRight="my_location">تحديث موقعي</Button>
            )}
          </Card>

          {shipment.status === 'delivered' ? (
            <Card className="mt-space-md"><EmptyState title="تم تسليم هذه الشحنة بالفعل." /></Card>
          ) : (
            <>
              {/* Method */}
              <section className="mt-space-lg">
                <SectionHeader title="طريقة التأكيد" />
                <Card className="mt-space-md flex flex-col gap-space-md">
                <div className="flex gap-space-xs">
                  {([['code', 'رمز العميل'], ['signature', 'توقيع']] as const).map(([m, lbl]) => (
                    <button key={m} type="button" onClick={() => setMethod(m)}
                      className={`px-3 py-1 rounded-full font-small ${method === m ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant'}`}>{lbl}</button>
                  ))}
                </div>
                <div>
                  {method === 'code' ? (
                    <Field label="رمز التأكيد" dir="ltr" mono value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="XXXXXXXX" />
                  ) : (
                    <Field label="اسم المستلِم / التوقيع" value={signature} onChange={(e) => setSignature(e.target.value)} />
                  )}
                </div>
                </Card>
              </section>

              {/* Shortages */}
              <section className="mt-space-lg">
                <SectionHeader title="نواقص أو تلف (اختياري)" />
                <Card className="mt-space-md flex flex-col gap-space-sm">
                  {shortages.map((r, i) => (
                    <div key={i} className="flex items-end gap-space-sm">
                      <div className="w-28"><Field label="رقم المنتج" dir="ltr" mono value={r.product_id} onChange={(e) => setShortage(i, { product_id: e.target.value })} /></div>
                      <div className="w-24"><Field label="الكمية" dir="ltr" mono value={r.qty} onChange={(e) => setShortage(i, { qty: e.target.value })} /></div>
                      <div className="flex-1 min-w-0"><Field label="ملاحظة" value={r.note} onChange={(e) => setShortage(i, { note: e.target.value })} /></div>
                      <button type="button" className="text-danger p-2" onClick={() => removeShortage(i)} aria-label="حذف"><Icon name="close" size={18} /></button>
                    </div>
                  ))}
                  <button type="button" onClick={addShortage} className="self-start font-small text-small text-primary hover:underline flex items-center gap-1">
                    <Icon name="add" size={16} /> إضافة نقص
                  </button>
                </Card>
              </section>

              <section className="mt-space-xl flex justify-end">
                <Button variant="primary" disabled={!canSubmit} onClick={() => void submit()}>تأكيد التسليم</Button>
              </section>
            </>
          )}
        </>
      )}
    </Narrow>
  )
}

import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, SectionHeader, Spinner, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import {
  addLeg, availableSlots, createSlot, setShipmentStatus, trackShipment, type Shipment, type Slot,
} from '../../api/logistics'
import { ApiError } from '../../api/client'
import { todayIso } from '../../lib/format'

const STATUS_AR: Record<string, string> = {
  scheduled: 'مجدول', shipped: 'تم الشحن', in_transit: 'في الطريق', delivered: 'تم التسليم', failed: 'فشل',
}

export function LogisticsPage() {
  const toast = useToast()
  const [slots, setSlots] = useState<Slot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [sd, setSd] = useState(todayIso())
  const [win, setWin] = useState('09:00-11:00')
  const [cap, setCap] = useState('10')
  const [orderId, setOrderId] = useState('')
  const [ship, setShip] = useState<Shipment | null>(null)
  const [legCarrier, setLegCarrier] = useState('external')
  const [legRef, setLegRef] = useState('')
  const [legFrom, setLegFrom] = useState('')
  const [legTo, setLegTo] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const to = new Date(); to.setDate(to.getDate() + 30)
      setSlots((await availableSlots(todayIso(), to.toISOString().slice(0, 10))).items)
    } catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  async function addSlot(e: FormEvent) {
    e.preventDefault(); setBusy(true)
    try { await createSlot(sd, win, Number(cap)); toast.success('أُضيف الموعد.'); await load() }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل') }
    finally { setBusy(false) }
  }

  async function lookup(e: FormEvent) {
    e.preventDefault(); setBusy(true)
    try { setShip(await trackShipment(Number(orderId))) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'لا توجد شحنة'); setShip(null) }
    finally { setBusy(false) }
  }

  async function run(fn: () => Promise<unknown>, msg: string) {
    setBusy(true)
    try { await fn(); toast.success(msg); if (ship) setShip(await trackShipment(ship.order_id)) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشلت العملية') }
    finally { setBusy(false) }
  }

  async function addLegSubmit(e: FormEvent) {
    e.preventDefault()
    if (!ship) return
    await run(
      () => addLeg(ship.id, {
        carrier_type: legCarrier,
        carrier_ref: legRef.trim() || undefined,
        from_label: legFrom.trim() || undefined,
        to_label: legTo.trim() || undefined,
      }),
      'أُضيف المسار.',
    )
    setLegRef(''); setLegFrom(''); setLegTo('')
  }

  return (
    <Wide>
      <PageTitle title="اللوجستيات" subtitle="مواعيد التسليم وإدارة الشحنات (أسطول داخلي / شحن خارجي)." />

      <section className="mt-space-xl">
        <SectionHeader title="إضافة موعد تسليم" />
        <form onSubmit={addSlot} className="flex flex-wrap items-end gap-space-md">
          <div className="w-40"><Field label="التاريخ" type="date" dir="ltr" value={sd} onChange={(e) => setSd(e.target.value)} /></div>
          <div className="w-36"><Field label="النافذة" dir="ltr" mono value={win} onChange={(e) => setWin(e.target.value)} /></div>
          <div className="w-24"><Field label="السعة" dir="ltr" mono value={cap} onChange={(e) => setCap(e.target.value)} /></div>
          <Button variant="primary" type="submit" disabled={busy}>إضافة</Button>
        </form>
        <div className="mt-space-md">
          {loading ? <Spinner /> : error ? <InlineError message={error} /> : (
            <DataTable rows={slots} rowKey={(s) => s.id} empty="لا توجد مواعيد متاحة." columns={[
              { header: 'التاريخ', cell: (s) => <Mono>{s.slot_date}</Mono> },
              { header: 'النافذة', cell: (s) => <Mono>{s.window}</Mono> },
              { header: 'المتاح', align: 'center', cell: (s) => <Mono>{s.remaining}/{s.capacity}</Mono> },
            ]} />
          )}
        </div>
      </section>

      <section className="mt-[48px]">
        <SectionHeader title="إدارة شحنة" />
        <form onSubmit={lookup} className="flex items-end gap-space-md">
          <div className="w-48"><Field label="رقم الطلب" dir="ltr" mono inputMode="numeric" value={orderId} onChange={(e) => setOrderId(e.target.value)} /></div>
          <Button variant="primary" type="submit" disabled={busy || !orderId}>عرض</Button>
        </form>
        {ship && (
          <div className="mt-space-md flex flex-col gap-space-md">
            <div className="flex items-center gap-space-sm">
              <Pill tone={ship.status === 'delivered' ? 'signal' : ship.status === 'failed' ? 'error' : 'warning'}>{STATUS_AR[ship.status] ?? ship.status}</Pill>
              <span className="font-body text-body text-secondary">{ship.carrier_type === 'internal' ? 'أسطول داخلي' : 'شحن خارجي'}</span>
            </div>
            <div className="flex flex-wrap gap-space-sm">
              {ship.status === 'scheduled' && <Button disabled={busy} onClick={() => run(() => setShipmentStatus(ship.id, 'shipped'), 'تم الشحن.')}>شحن</Button>}
              {(ship.status === 'shipped' || ship.status === 'scheduled') && <Button disabled={busy} onClick={() => run(() => setShipmentStatus(ship.id, 'in_transit'), 'في الطريق.')}>في الطريق</Button>}
            </div>
            <form onSubmit={addLegSubmit} className="flex flex-wrap items-end gap-space-sm border-t border-surface-container-high pt-space-md">
              <div className="w-36">
                <label className="block font-small text-small text-secondary mb-1">الناقل</label>
                <select value={legCarrier} onChange={(e) => setLegCarrier(e.target.value)}
                  className="w-full bg-transparent border-b border-surface-container-high py-1.5 font-body text-body text-primary focus:outline-none focus:border-primary">
                  <option value="internal">أسطول داخلي</option>
                  <option value="external">شحن خارجي</option>
                </select>
              </div>
              <div className="w-40"><Field label="مرجع الناقل" value={legRef} onChange={(e) => setLegRef(e.target.value)} /></div>
              <div className="w-40"><Field label="من" value={legFrom} onChange={(e) => setLegFrom(e.target.value)} /></div>
              <div className="w-40"><Field label="إلى" value={legTo} onChange={(e) => setLegTo(e.target.value)} /></div>
              <Button type="submit" disabled={busy}>+ إضافة مسار</Button>
            </form>
            {ship.legs.length > 0 && (
              <DataTable rows={ship.legs} rowKey={(l) => l.seq} columns={[
                { header: 'المسار', cell: (l) => `${l.from_label ?? '—'} ← ${l.to_label ?? '—'}` },
                { header: 'الناقل', align: 'center', cell: (l) => (l.carrier_type === 'internal' ? 'داخلي' : 'خارجي') },
              ]} />
            )}
          </div>
        )}
      </section>
    </Wide>
  )
}

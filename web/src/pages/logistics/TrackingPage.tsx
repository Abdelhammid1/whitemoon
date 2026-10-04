import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, EmptyState, InlineError } from '../../components/ui'
import { Mono } from '../../components/DataTable'
import { trackShipment, type Shipment } from '../../api/logistics'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

const STEPS = ['scheduled', 'shipped', 'in_transit', 'delivered']
const STATUS_AR: Record<string, string> = {
  scheduled: 'مجدول', shipped: 'تم الشحن', in_transit: 'في الطريق', delivered: 'تم التسليم', failed: 'فشل',
}

export function TrackingPage() {
  const { id } = useParams()
  const [ship, setShip] = useState<Shipment | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [missing, setMissing] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setShip(await trackShipment(Number(id))) }
    catch (err) {
      if (err instanceof ApiError && err.status === 404) setMissing(true)
      else setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally { setLoading(false) }
  }, [id])
  useEffect(() => { void load() }, [load])

  if (loading) return <Narrow><Spinner /></Narrow>
  if (missing) return <Narrow><PageTitle title="تتبع الشحنة" /><div className="mt-space-xl"><EmptyState title="لا توجد شحنة لهذا الطلب بعد." description="سيظهر التتبع بعد جدولة التسليم." /></div></Narrow>
  if (error || !ship) return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>

  const stepIdx = STEPS.indexOf(ship.status)

  return (
    <Narrow>
      <PageTitle title={`تتبع شحنة الطلب #${ship.order_id}`} />
      <div className="mt-space-sm flex items-center gap-space-sm">
        <Pill tone={ship.status === 'delivered' ? 'signal' : ship.status === 'failed' ? 'error' : 'warning'}>{STATUS_AR[ship.status] ?? ship.status}</Pill>
        <span className="font-body text-body text-secondary">{ship.carrier_type === 'internal' ? 'أسطول داخلي' : 'شحن خارجي'}</span>
      </div>

      <section className="mt-space-xl flex flex-col gap-space-sm">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-space-md">
            <span className={`w-2.5 h-2.5 rounded-full ${i <= stepIdx ? 'bg-[#0F6B3E]' : 'bg-surface-container-highest'}`} />
            <span className={`font-body text-body ${i <= stepIdx ? 'text-on-surface' : 'text-secondary'}`}>{STATUS_AR[s]}</span>
          </div>
        ))}
      </section>

      {ship.current_lat && (
        <p className="mt-space-lg font-mono-body text-mono-body text-secondary">
          الموقع الحالي: <bdi dir="ltr">{ship.current_lat}, {ship.current_lng}</bdi>
          {ship.location_updated_at && <> — {formatDate(ship.location_updated_at)}</>}
        </p>
      )}

      {ship.confirmation_code && (
        <div className="mt-space-lg rounded-xl bg-surface-container-low p-space-md">
          <span className="font-small text-small text-secondary">سلّم هذا الرمز للمندوب عند الاستلام</span>
          <div className="font-display text-display text-primary tracking-widest"><Mono>{ship.confirmation_code}</Mono></div>
        </div>
      )}
    </Narrow>
  )
}

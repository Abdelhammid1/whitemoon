import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, EmptyState, InlineError, Card } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { Mono } from '../../components/DataTable'
import { ShipmentMap } from '../../components/ShipmentMap'
import { trackShipment, type Shipment } from '../../api/logistics'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

const STEPS = ['scheduled', 'shipped', 'in_transit', 'delivered'] as const
const STATUS_AR: Record<string, string> = {
  scheduled: 'مجدول', shipped: 'تم الشحن', in_transit: 'في الطريق', delivered: 'تم التسليم', failed: 'فشل التسليم',
}
/* step → descriptive label + icon (meaning of the stage, not fabricated data) */
const STEP_DESC: Record<(typeof STEPS)[number], { title: string; note: string; icon: string }> = {
  scheduled: { title: 'مجدول — تجهيز وتثبيت بنود الشحنة', note: 'تم جرد الأصناف وتثبيتها على منصات الشحن بالمستودع.', icon: 'inventory_2' },
  shipped: { title: 'تم الشحن — مغادرة المستودع', note: 'إصدار بوليصة النقل وخروج الشاحنة من مستودع العبور.', icon: 'local_shipping' },
  in_transit: { title: 'في الطريق — المندوب متجه لموقع العميل', note: 'مركبة الشحن في طريقها إلى وجهة التسليم المسجّلة.', icon: 'near_me' },
  delivered: { title: 'تم التسليم — إدخال رمز التأكيد والمطابقة', note: 'تفريغ الشحنة بمقر المستلم وإقفال العهدة برمز التأكيد.', icon: 'verified' },
}

/** Only allow http(s) links; reject javascript:/data:/etc. so a server-supplied
 *  URL can never execute when clicked. */
function safeHttpUrl(u?: string | null): string | null {
  try {
    const p = new URL(u ?? '', window.location.origin)
    return p.protocol === 'https:' || p.protocol === 'http:' ? p.href : null
  } catch {
    return null
  }
}

type NodeState = 'done' | 'active' | 'pending' | 'failed'

function StationNode({ state, icon }: { state: NodeState; icon: string }) {
  if (state === 'failed')
    return (
      <div className="relative z-10 w-6 h-6 rounded-full bg-error flex items-center justify-center text-on-error shrink-0">
        <Icon name="close" size={16} />
      </div>
    )
  if (state === 'done')
    return (
      <div className="relative z-10 w-6 h-6 rounded-full bg-primary flex items-center justify-center text-on-primary shrink-0">
        <Icon name="check" size={16} />
      </div>
    )
  if (state === 'active')
    return (
      <div className="relative z-10 w-6 h-6 rounded-full bg-primary ring-4 ring-surface-container-high flex items-center justify-center text-on-primary shrink-0 animate-pulse">
        <Icon name={icon} size={15} />
      </div>
    )
  return (
    <div className="relative z-10 w-6 h-6 rounded-full bg-surface-container-highest flex items-center justify-center text-secondary shrink-0">
      <Icon name={icon} size={16} />
    </div>
  )
}

export function TrackingPage() {
  const { id } = useParams()
  const [ship, setShip] = useState<Shipment | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [missing, setMissing] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async () => {
    setRefreshing(true); setError(null)
    try { setShip(await trackShipment(Number(id))) }
    catch (err) {
      if (err instanceof ApiError && err.status === 404) setMissing(true)
      else setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally { setLoading(false); setRefreshing(false) }
  }, [id])
  useEffect(() => { void load() }, [load])

  // Live tracking: poll for the rep's latest location until delivered/failed.
  useEffect(() => {
    const st = ship?.status
    if (!st || st === 'delivered' || st === 'failed') return
    const t = setInterval(() => { void load() }, 20000)
    return () => clearInterval(t)
  }, [ship?.status, load])

  if (loading) return <Narrow><Spinner /></Narrow>
  if (missing)
    return (
      <Narrow>
        <PageTitle title="تتبع الشحنة" />
        <div className="mt-space-xl"><EmptyState title="لا توجد شحنة لهذا الطلب بعد." description="سيظهر التتبع بعد جدولة التسليم." /></div>
      </Narrow>
    )
  if (error || !ship)
    return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>

  const status = ship.status
  const isFailed = status === 'failed'
  const activeIdx = STEPS.indexOf(status as (typeof STEPS)[number])
  const statusTone = status === 'delivered' ? 'signal' : isFailed ? 'error' : 'warning'

  function stationState(i: number): NodeState {
    if (isFailed) return i === 3 ? 'failed' : 'done'
    if (i < activeIdx) return 'done'
    if (i === activeIdx) return status === 'delivered' ? 'done' : 'active'
    return 'pending'
  }

  return (
    <Narrow>
      <div className="flex flex-col gap-space-lg w-full">
        {/* Header */}
        <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-space-md pb-space-md border-b border-surface-container-highest">
          <div className="flex flex-col gap-space-xs">
            <div className="flex items-center gap-space-sm">
              <Mono className="text-secondary">#{ship.order_id}</Mono>
              <span className="w-1.5 h-1.5 rounded-full bg-secondary-fixed-dim" />
              <span className="font-small text-small text-secondary">
                {ship.carrier_type === 'internal' ? 'أسطول وايت مون الداخلي' : 'شحن خارجي معتمد'}
              </span>
            </div>
            <div className="flex items-center gap-space-md flex-wrap">
              <h1 className="font-display text-display text-primary font-medium tracking-tight">
                تتبع شحنة الطلب #{ship.order_id}
              </h1>
              <Pill tone={statusTone}>{STATUS_AR[ship.status] ?? ship.status}</Pill>
            </div>
          </div>
          <button
            onClick={() => void load()}
            disabled={refreshing}
            className="inline-flex items-center gap-1 px-space-md py-2 rounded-lg bg-surface-container-low text-primary hover:bg-surface-container font-body-medium text-body-medium transition-colors disabled:opacity-40"
          >
            <Icon name="sync" size={18} className={refreshing ? 'animate-spin' : ''} />
            <span>تحديث لحظي</span>
          </button>
        </header>

        {/* Metadata strip — only fields the backend actually provides */}
        <Card className="grid grid-cols-2 md:grid-cols-3 gap-space-md">
          <div className="flex flex-col">
            <span className="font-small text-small text-secondary">الناقل اللوجستي</span>
            <span className="font-body-medium text-body-medium text-primary mt-1">
              {ship.carrier_type === 'internal' ? 'أسطول وايت مون المركزي' : 'ناقل خارجي'}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="font-small text-small text-secondary">تاريخ التسليم</span>
            <span className="font-mono-body text-mono-body text-primary mt-1" dir="ltr">
              {ship.delivered_at ? formatDate(ship.delivered_at) : '—'}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="font-small text-small text-secondary">آخر تحديث للموقع</span>
            <span className="font-mono-body text-mono-body text-primary mt-1" dir="ltr">
              {ship.location_updated_at ? formatDate(ship.location_updated_at) : '—'}
            </span>
          </div>
        </Card>

        {/* Secure delivery confirmation key card */}
        {ship.confirmation_code && (
          <Card className="flex flex-col md:flex-row items-center justify-between gap-space-lg">
            <div className="flex flex-col gap-1 max-w-xl text-right">
              <div className="flex items-center gap-space-xs text-primary font-headline-2 text-headline-2">
                <Icon name="verified_user" size={20} />
                <span>رمز المطابقة والتسليم الأمني</span>
              </div>
              <p className="font-body text-body text-secondary mt-1">
                سلّم هذا الرمز لمندوب التسليم بعد مطابقة بنود الشحنة للتحقق النهائي وإقفال العهدة. لا تشاركه هاتفياً قبل الفحص المادي.
              </p>
            </div>
            <div className="flex flex-col items-center justify-center p-space-md min-w-[240px]">
              <span className="font-small text-small text-secondary tracking-widest mb-1">Passcode / رمز التحقق</span>
              <div className="bg-surface-container-low px-4 py-1.5 font-mono-medium text-[32px] leading-tight tracking-[0.2em] text-primary" dir="ltr">
                {ship.confirmation_code}
              </div>
              <div className="mt-2 flex items-center gap-1.5 text-secondary font-mono-body text-small" dir="ltr">
                <Icon name="lock" size={14} />
                <span>ORDER #{ship.order_id} ONLY</span>
              </div>
            </div>
          </Card>
        )}

        {/* Live location map (US-9.2) — free OpenStreetMap, polled above */}
        {ship.current_lat && ship.current_lng && (
          <Card className="flex flex-col gap-space-sm">
            <div className="flex items-center justify-between">
              <h2 className="font-headline-2 text-headline-2 text-primary">الموقع الحي للمندوب</h2>
              {ship.location_updated_at && (
                <span className="font-mono-body text-small text-secondary" dir="ltr">
                  {formatDate(ship.location_updated_at)}
                </span>
              )}
            </div>
            <ShipmentMap lat={Number(ship.current_lat)} lng={Number(ship.current_lng)} />
          </Card>
        )}

        {/* Chronological timeline */}
        <Card className="flex flex-col gap-space-md">
          <h2 className="font-headline-2 text-headline-2 text-primary pb-space-xs">المسار اللوجستي والخط الزمني</h2>
          <div className="relative flex flex-col gap-0 pr-2">
            {STEPS.map((s, i) => {
              const state = stationState(i)
              const desc = STEP_DESC[s]
              const lineDone = isFailed ? i < 3 : i < activeIdx
              const isActive = state === 'active'
              return (
                <div key={s} className="relative flex items-start gap-space-md pb-space-lg last:pb-0">
                  {i < STEPS.length - 1 && (
                    <div className={`absolute right-[11px] top-6 bottom-0 w-[2px] ${lineDone ? 'bg-primary' : 'bg-surface-container-highest'}`} />
                  )}
                  <StationNode state={state === 'failed' ? 'failed' : state} icon={desc.icon} />
                  <div className={`flex flex-col flex-1 min-w-0 pr-space-xs ${isActive ? 'bg-surface-container-low p-space-md' : ''}`}>
                    <div className="flex items-baseline justify-between gap-space-xs">
                      <span className={`font-body-medium text-body-medium ${state === 'pending' ? 'text-secondary' : state === 'failed' ? 'text-error' : 'text-primary'}`}>
                        {state === 'failed' ? STATUS_AR.failed : desc.title}
                      </span>
                      {s === 'delivered' && ship.delivered_at && state === 'done' && (
                        <span className="font-mono-body text-mono-body text-secondary" dir="ltr">{formatDate(ship.delivered_at)}</span>
                      )}
                      {isActive && ship.location_updated_at && (
                        <span className="font-mono-body text-mono-body text-primary font-medium" dir="ltr">{formatDate(ship.location_updated_at)}</span>
                      )}
                    </div>
                    <p className="font-small text-small text-secondary mt-0.5">{desc.note}</p>
                    {isActive && ship.current_lat && ship.current_lng && (
                      <div className="mt-space-sm flex items-center gap-space-xs font-mono-body text-small text-primary" dir="ltr">
                        <Icon name="near_me" size={14} />
                        <span>{ship.current_lat}, {ship.current_lng}</span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </Card>

        {/* Route legs (external hops) — real data only */}
        {ship.legs.length > 0 && (
          <Card className="flex flex-col gap-space-sm">
            <h2 className="font-headline-2 text-headline-2 text-primary pb-space-xs">مسارات النقل الخارجية</h2>
            <div className="flex flex-col divide-y divide-surface-container">
              {ship.legs.map((leg) => (
                <div key={leg.seq} className="flex items-center justify-between py-space-sm gap-space-md font-small text-small">
                  <div className="flex items-center gap-space-sm min-w-0">
                    <Mono className="text-secondary">#{leg.seq}</Mono>
                    <span className="text-on-surface truncate">
                      {leg.from_label ?? '—'} <span className="text-secondary">←</span> {leg.to_label ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center gap-space-sm shrink-0">
                    {leg.carrier_ref && <Mono className="text-secondary">{leg.carrier_ref}</Mono>}
                    <Pill tone={leg.status === 'delivered' ? 'signal' : leg.status === 'failed' ? 'error' : 'neutral'}>
                      {STATUS_AR[leg.status] ?? leg.status}
                    </Pill>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Reported shortages / damage — real data only (failed/partial deliveries) */}
        {ship.shortages.length > 0 && (
          <Card className="flex flex-col gap-space-sm">
            <div className="flex items-center gap-space-xs text-error font-headline-2 text-headline-2 pb-space-xs">
              <Icon name="report" size={18} />
              <span>نواقص أو تلف مُبلّغ عنه</span>
            </div>
            <div className="flex flex-col divide-y divide-surface-container">
              {ship.shortages.map((sh, i) => {
                const photo = safeHttpUrl(sh.photo_url)
                return (
                  <div key={i} className="flex items-center justify-between py-space-sm gap-space-md font-small text-small">
                    <div className="flex items-center gap-space-sm min-w-0">
                      <span className="text-on-surface">صنف</span>
                      <Mono className="text-secondary">#{sh.product_id}</Mono>
                      {sh.note && <span className="text-secondary truncate">— {sh.note}</span>}
                    </div>
                    <div className="flex items-center gap-space-sm shrink-0">
                      <Mono className="text-error">{sh.qty}</Mono>
                      {photo && (
                        <a href={photo} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline inline-flex items-center gap-1">
                          <Icon name="image" size={14} /> صورة
                        </a>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>
        )}
      </div>
    </Narrow>
  )
}

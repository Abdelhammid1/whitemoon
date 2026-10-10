import { useEffect, useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Wide } from '../layouts/AppShell'
import { Card, Pill, Spinner, InlineError } from '../components/ui'
import { Icon } from '../components/Icon'
import { PageHelp } from '../components/PageHelp'
import { useAuth } from '../auth/AuthContext'
import { listPendingSuppliers } from '../api/admin'
import { getDashboard, type Dashboard } from '../api/bi'
import { getSupplierSummary, advanceSubOrder, type SupplierSummary } from '../api/commerce'
import { ApiError } from '../api/client'
import { useToast } from '../components/Toast'
import { formatMoney, formatNumber } from '../lib/format'

const QUICK_LINKS_SUPPLIER = [
  { to: '/supplier/orders', label: 'طلبات واردة', icon: 'inbox' },
  { to: '/supplier/products', label: 'منتجاتي (السعر والكمية والخصم)', icon: 'inventory_2' },
]
const QUICK_LINKS_CUSTOMER = [
  { to: '/catalog', label: 'تصفّح السوق', icon: 'storefront' },
  { to: '/cart', label: 'سلتي', icon: 'shopping_cart' },
  { to: '/orders', label: 'طلباتي', icon: 'list_alt' },
  { to: '/rfq', label: 'طلب عرض سعر', icon: 'request_quote' },
]

function fullDate(): string {
  try {
    return new Intl.DateTimeFormat('ar-EG', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date())
  } catch {
    return ''
  }
}
function greeting(): string {
  const h = new Date().getHours()
  if (h < 12) return 'صباح الخير'
  if (h < 18) return 'طاب يومك'
  return 'مساء الخير'
}
const arNum = (n: number) => {
  try { return new Intl.NumberFormat('ar-EG').format(n) } catch { return String(n) }
}

/* ---------------------------------------------------------- KPI tile */
function Tile({ icon, label, value, unit, hint, tone = 'neutral', accent }: {
  icon: string; label: string; value: ReactNode; unit?: string; hint?: ReactNode
  tone?: 'neutral' | 'signal' | 'warning' | 'error'; accent?: boolean
}) {
  const chip = accent ? 'bg-gold-weak text-gold' : 'bg-brand-weak text-primary'
  const hintCls = tone === 'error' ? 'text-danger' : tone === 'warning' ? 'text-warning' : tone === 'signal' ? 'text-signal' : 'text-secondary'
  return (
    <Card className="flex flex-col gap-space-md min-h-[150px]">
      <span className={`w-10 h-10 rounded-xl flex items-center justify-center ${chip}`}><Icon name={icon} size={20} /></span>
      <div className="flex items-baseline gap-space-xs">
        <span className={`font-mono-medium text-display tracking-tight ${tone === 'error' ? 'text-danger' : 'text-on-surface'}`} dir="ltr">{value}</span>
        {unit && <span className={`font-small text-small ${tone === 'error' ? 'text-danger' : 'text-secondary'}`}>{unit}</span>}
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="font-body-medium text-body-medium text-on-surface">{label}</span>
        {hint && <span className={`font-small text-small ${hintCls}`}>{hint}</span>}
      </div>
    </Card>
  )
}

/* ---------------------------------------------------------- weekly chart */
function WeeklyChart({ weekly }: { weekly: { date: string; total: string }[] }) {
  const totals = weekly.map((w) => Number(w.total) || 0)
  const max = Math.max(...totals, 1)
  const total = totals.reduce((s, v) => s + v, 0)
  const baseY = 150, top = 20, chartH = baseY - top, left = 48, right = 512
  const step = (right - left - 20) / weekly.length
  const barW = Math.min(40, step * 0.6)
  const dayLabel = (iso: string) => {
    try { return new Intl.DateTimeFormat('ar-EG', { weekday: 'short' }).format(new Date(iso)) } catch { return '' }
  }
  const grid = [0, 1 / 3, 2 / 3, 1]
  return (
    <Card>
      <div className="flex items-center justify-between gap-space-md mb-space-md">
        <div><h3 className="font-headline-2 text-headline-2 text-on-surface">المبيعات خلال الأسبوع</h3>
          <p className="font-small text-small text-secondary mt-0.5">آخر ٧ أيام</p></div>
        <Pill tone="gold">إجمالي {formatNumber(String(total))} ج.م</Pill>
      </div>
      <svg viewBox="0 0 520 180" width="100%" style={{ display: 'block' }} role="img" aria-label="مبيعات الأسبوع">
        {grid.map((g, i) => {
          const y = baseY - g * chartH
          return (
            <g key={i}>
              <line x1={left} y1={y} x2={right} y2={y} className="stroke-surface-container-high" />
              <text x={left - 8} y={y + 4} textAnchor="end" fontFamily="JetBrains Mono" fontSize="10" className="fill-secondary">{arNum(Math.round((max * g) / 1000))}</text>
            </g>
          )
        })}
        {weekly.map((w, i) => {
          const h = ((totals[i] ?? 0) / max) * chartH
          const x = left + 10 + i * step + (step - barW) / 2
          const y = baseY - h
          const isToday = i === weekly.length - 1
          return (
            <g key={w.date}>
              <rect x={x} y={y} width={barW} height={Math.max(0, h)} rx="5" className={isToday ? 'fill-primary' : 'fill-brand-weak'} />
              {isToday && <circle cx={x + barW / 2} cy={y} r="3.5" className="fill-gold" />}
              <text x={x + barW / 2} y={168} textAnchor="middle" fontFamily="IBM Plex Sans Arabic" fontSize="11" className="fill-secondary">{dayLabel(w.date)}</text>
            </g>
          )
        })}
      </svg>
    </Card>
  )
}

/* ---------------------------------------------------------- tier distribution */
const TIERS: { code: string; label: string; color: string }[] = [
  { code: 'green', label: 'أخضر — ممتاز', color: 'var(--c-signal)' },
  { code: 'white', label: 'أبيض — جديد', color: 'var(--c-faint)' },
  { code: 'yellow', label: 'أصفر — تنبيه', color: 'var(--c-warning)' },
  { code: 'red', label: 'أحمر — محظور', color: 'var(--c-error)' },
]
const TIER_BAR: Record<string, string> = { green: 'bg-signal', white: 'bg-outline', yellow: 'bg-warning', red: 'bg-danger' }
const TIER_DOT: Record<string, string> = { green: 'bg-signal', white: 'bg-outline', yellow: 'bg-warning', red: 'bg-danger' }

function TierDistribution({ dist }: { dist: Record<string, number> }) {
  const total = Object.values(dist).reduce((s, v) => s + v, 0)
  const max = Math.max(...Object.values(dist), 1)
  return (
    <Card>
      <div className="mb-space-md"><h3 className="font-headline-2 text-headline-2 text-on-surface">توزيع التصنيف الائتماني</h3>
        <p className="font-small text-small text-secondary mt-0.5">{arNum(total)} عميلًا نشطًا</p></div>
      <div className="flex flex-col gap-space-md">
        {TIERS.map((t) => {
          const v = dist[t.code] ?? 0
          return (
            <div key={t.code}>
              <div className="flex items-center justify-between font-small text-small mb-1">
                <span className="flex items-center gap-space-xs text-secondary">
                  <span className={`w-2 h-2 rounded-full ${TIER_DOT[t.code]}`} />{t.label}
                </span>
                <span className="font-mono-body text-on-surface" dir="ltr">{arNum(v)}</span>
              </div>
              <div className="h-1.5 rounded-pill bg-surface-container overflow-hidden">
                <div className={`h-full rounded-pill ${TIER_BAR[t.code]}`} style={{ width: `${Math.max(v ? 6 : 0, (v / max) * 100)}%` }} />
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

/* ---------------------------------------------------------- admin dashboard */
function AdminDashboard() {
  const navigate = useNavigate()
  const [d, setD] = useState<Dashboard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDashboard().then(setD).catch((e) => setError(e instanceof ApiError ? e.message : 'تعذّر التحميل')).finally(() => setLoading(false))
  }, [])

  if (loading) return <Wide><Spinner /></Wide>
  if (error || !d) return <Wide><div className="mt-space-xl"><InlineError message={error ?? 'غير متاح'} /></div></Wide>

  const today = Number(d.sales.today) || 0
  const yesterday = Number(d.sales.weekly[d.sales.weekly.length - 2]?.total) || 0
  const delta = yesterday > 0 ? ((today - yesterday) / yesterday) * 100 : null
  const overdue = (Number(d.collection.overdue) || 0) + (Number(d.collection.defaulted) || 0)
  const redCustomers = d.credit.tier_distribution.red ?? 0

  return (
    <Wide>
      <header className="flex flex-wrap items-end justify-between gap-space-md">
        <div>
          <h1 className="font-display text-display text-on-surface font-medium tracking-tight">{greeting()} <span className="text-gold">🌙</span></h1>
          <p className="font-body text-body text-secondary mt-space-xs">ملخّص الأداء ليوم {fullDate()} — كل القيم بالجنيه المصري.</p>
        </div>
        <button onClick={() => navigate('/accounting/journal/manual')}
          className="inline-flex items-center gap-space-sm rounded-lg py-2 px-4 bg-primary text-on-primary font-body-medium text-body-medium shadow-card-sm hover:bg-primary-container transition-colors">
          <Icon name="add" size={18} /> قيد جديد
        </button>
      </header>

      <PageHelp pageKey="home" />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-space-md mt-space-xl">
        <Tile icon="payments" accent label="مبيعات اليوم" value={formatNumber(d.sales.today)} unit="ج.م" tone={delta != null && delta < 0 ? 'error' : 'signal'}
          hint={delta == null ? 'أول مبيعات اليوم' : `${delta >= 0 ? '▲' : '▼'} ${arNum(Math.abs(Math.round(delta * 10) / 10))}٪ عن أمس`} />
        <Tile icon="orders" label="الطلبات المفتوحة" value={arNum(d.sales.open_orders)} tone="warning"
          hint="بانتظار التأكيد أو التجهيز" />
        <Tile icon="request_quote" label="متأخرات التحصيل" value={formatNumber(String(overdue))} unit="ج.م" tone="error"
          hint={`${arNum(redCustomers)} عملاء متجاوزون`} />
        <Tile icon="notification_important" label="تنبيهات المخزون" value={arNum(d.inventory.low_stock_slots)} tone="warning"
          hint="أصناف تحت حد الأمان" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-space-md mt-space-md">
        <div className="lg:col-span-3"><WeeklyChart weekly={d.sales.weekly} /></div>
        <div className="lg:col-span-2"><TierDistribution dist={d.credit.tier_distribution} /></div>
      </div>
    </Wide>
  )
}

/* ---------------------------------------------------------- supplier dashboard (T-41) */
function SupplierDashboard() {
  const navigate = useNavigate()
  const toast = useToast()
  const [s, setS] = useState<SupplierSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(0)

  async function load() {
    try { setS(await getSupplierSummary()) } catch { /* keep quick links only */ }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])

  async function act(subId: number, action: 'confirm' | 'ready') {
    setBusy(subId)
    try { await advanceSubOrder(subId, action); toast.success(action === 'confirm' ? 'تم تأكيد الطلب.' : 'تم وسمه جاهزًا للتسليم.'); await load() }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّرت العملية') }
    finally { setBusy(0) }
  }

  return (
    <Wide>
      <header className="flex flex-col">
        <h1 className="font-display text-display text-on-surface font-medium tracking-tight">{greeting()} <span className="text-gold">🌙</span></h1>
        <p className="font-body text-body text-secondary mt-space-xs">تعرض هذه الصفحة ما يحتاج إجراءً منك الآن. اضغط على أي بطاقة للانتقال مباشرة.</p>
      </header>
      <PageHelp pageKey="supplier-home" />

      {loading ? <div className="mt-space-xl"><Spinner /></div> : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md mt-space-xl">
            <button onClick={() => navigate('/supplier/orders')} className="text-start">
              <Tile icon="inbox" accent label="طلبات جديدة تنتظر التأكيد" value={arNum(s?.counts.new_orders ?? 0)} tone="warning" hint="اضغط للانتقال" />
            </button>
            <button onClick={() => navigate('/supplier/products')} className="text-start">
              <Tile icon="warning" label="أصناف قاربت على النفاد" value={arNum(s?.counts.low_stock ?? 0)} tone="error" hint="راجع المخزون" />
            </button>
            <button onClick={() => navigate('/supplier/products')} className="text-start">
              <Tile icon="schedule" label="خصومات ستنتهي قريبًا" value={arNum(s?.counts.expiring_discounts ?? 0)} tone="neutral" hint="خلال ٧ أيام" />
            </button>
          </div>

          {s && s.new_orders.length > 0 && (
            <Card className="mt-space-md flex flex-col gap-space-sm">
              <h3 className="font-headline-2 text-headline-2 text-on-surface">طلبات تنتظر إجراءك</h3>
              <div className="flex flex-col divide-y divide-surface-container">
                {s.new_orders.map((o) => (
                  <div key={o.sub_order_id} className="flex items-center justify-between py-space-sm gap-space-md">
                    <span className="font-body text-body text-on-surface">طلب {o.order_number} — <span className="font-mono-body" dir="ltr">{formatMoney(o.subtotal)} ج.م</span></span>
                    <span className="flex items-center gap-space-md">
                      <button className="text-primary font-small-medium hover:underline disabled:opacity-40" disabled={busy === o.sub_order_id} onClick={() => void act(o.sub_order_id, 'confirm')}>تأكيد</button>
                      <button className="text-primary font-small-medium hover:underline disabled:opacity-40" disabled={busy === o.sub_order_id} onClick={() => void act(o.sub_order_id, 'ready')}>جاهز للتسليم</button>
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <nav className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-space-md mt-space-md">
            {QUICK_LINKS_SUPPLIER.map((l) => (
              <Link key={l.to} to={l.to} className="group">
                <Card padded={false} className="h-full p-space-lg flex items-center gap-space-md transition-shadow group-hover:shadow-overlay">
                  <span className="w-10 h-10 rounded-xl bg-brand-weak flex items-center justify-center shrink-0"><Icon name={l.icon} size={20} className="text-primary" /></span>
                  <span className="font-body-medium text-body-medium text-on-surface flex-1 min-w-0">{l.label}</span>
                  <Icon name="arrow_back" size={18} className="text-outline group-hover:text-primary transition-colors" />
                </Card>
              </Link>
            ))}
          </nav>
        </>
      )}
    </Wide>
  )
}

/* ---------------------------------------------------------- quick links (non-admin) */
function QuickLinks({ links }: { links: { to: string; label: string; icon: string }[] }) {
  return (
    <Wide>
      <header className="flex flex-col">
        <h1 className="font-display text-display text-on-surface font-medium tracking-tight">أهلاً بك في وايت مون <span className="text-gold">🌙</span></h1>
        <p className="font-body text-body text-secondary mt-space-xs">روابطك المباشرة على منصّة وايت مون.</p>
      </header>
      <PageHelp pageKey="home" />
      <nav className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-space-md mt-space-xl">
        {links.map((l) => (
          <Link key={l.to} to={l.to} className="group">
            <Card padded={false} className="h-full p-space-lg flex items-center gap-space-md transition-shadow group-hover:shadow-overlay">
              <span className="w-10 h-10 rounded-xl bg-brand-weak flex items-center justify-center shrink-0"><Icon name={l.icon} size={20} className="text-primary" /></span>
              <span className="font-body-medium text-body-medium text-on-surface flex-1 min-w-0">{l.label}</span>
              <Icon name="arrow_back" size={18} className="text-outline group-hover:text-primary transition-colors" />
            </Card>
          </Link>
        ))}
      </nav>
    </Wide>
  )
}

export function HomePage() {
  const { user } = useAuth()
  const isAdmin = user?.kind === 'admin' || user?.kind === 'staff'
  const [, setPending] = useState<number | null>(null)

  useEffect(() => {
    if (!isAdmin) return
    listPendingSuppliers().then((r) => setPending(r.items.length)).catch(() => setPending(null))
  }, [isAdmin])

  if (!user) return null
  if (isAdmin) return <AdminDashboard />
  if (user.kind === 'supplier') return <SupplierDashboard />
  return <QuickLinks links={QUICK_LINKS_CUSTOMER} />
}

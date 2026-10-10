import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'
import { Icon } from '../components/Icon'
import logoUrl from '../assets/white-moon-logo.png'
import { ImpersonationBanner } from '../components/ImpersonationBanner'
import { AssistantWidget } from '../components/assistant/AssistantWidget'
import { getMyCredit, type MyCredit } from '../api/credit'
import { formatMoney } from '../lib/format'

interface NavEntry {
  to: string
  label: string
  icon: string
  end?: boolean
  /** Optional per-item gate, narrower than the group's roles. */
  roles?: string[]
  /** Optional capability gate: show only if the user holds this permission. */
  perm?: string
}
interface NavGroup {
  label: string
  items: NavEntry[]
  roles: string[]
}

const GROUPS: NavGroup[] = [
  {
    label: 'النظام',
    roles: ['admin', 'staff'],
    items: [
      { to: '/home', label: 'لوحة التحكم', icon: 'space_dashboard', end: true },
      { to: '/dashboard', label: 'التحليلات التنفيذية', icon: 'monitoring' },
      { to: '/admin/orders', label: 'كل الطلبات', icon: 'receipt_long' },
      { to: '/admin/users', label: 'المستخدمون', icon: 'group' },
      { to: '/admin/suppliers/pending', label: 'الموردون المعلقون', icon: 'how_to_reg' },
      { to: '/admin/audit', label: 'سجل التدقيق', icon: 'history' },
      { to: '/admin/system-settings', label: 'إعدادات النظام', icon: 'tune', perm: 'system.settings.manage' },
      { to: '/assistant', label: 'مساعد المدير', icon: 'smart_toy', roles: ['admin'] },
      { to: '/assistant/gaps', label: 'فجوات المعرفة', icon: 'quiz', roles: ['admin'] },
      { to: '/comm/moderation', label: 'مراقبة المحادثات', icon: 'gpp_maybe' },
      { to: '/admin/impersonation', label: 'الدخول كمستخدم', icon: 'switch_account' },
    ],
  },
  {
    label: 'المالية',
    roles: ['admin', 'staff'],
    items: [
      { to: '/accounting/chart', label: 'دليل الحسابات', icon: 'account_tree' },
      { to: '/accounting/periods', label: 'الفترات المالية', icon: 'calendar_month' },
      { to: '/accounting/journal/manual', label: 'قيد يدوي', icon: 'edit_note' },
      { to: '/accounting/receipts', label: 'الإيصالات والعمليات', icon: 'receipt_long' },
      { to: '/accounting/deferred', label: 'البيع الآجل', icon: 'payments' },
      { to: '/accounting/reports', label: 'التقارير', icon: 'summarize' },
    ],
  },
  {
    label: 'الائتمان والعملاء',
    roles: ['admin', 'staff'],
    items: [
      { to: '/credit', label: 'التصنيف الائتماني', icon: 'credit_score' },
      { to: '/credit/dunning', label: 'المتابعة والتحصيل', icon: 'request_quote' },
      { to: '/credit/payments', label: 'اعتماد السداد', icon: 'price_check' },
      { to: '/credit/tiers', label: 'سقوف التصنيف', icon: 'tune' },
      { to: '/credit/deferred-settings', label: 'إعدادات البيع الآجل', icon: 'payments', perm: 'deferred.settings.manage' },
      { to: '/compliance', label: 'جاهزية ETA', icon: 'verified' },
    ],
  },
  {
    label: 'المستودع',
    roles: ['admin', 'staff'],
    items: [
      { to: '/inventory/categories', label: 'الفئات', icon: 'category' },
      { to: '/inventory/products', label: 'المنتجات والمخزون', icon: 'inventory_2' },
      { to: '/inventory/coding-queue', label: 'طابور التكويد', icon: 'assignment_add' },
      { to: '/inventory/stock', label: 'أرصدة المخزون', icon: 'warehouse' },
      { to: '/inventory/reorder', label: 'تنبيهات إعادة الطلب', icon: 'notification_important' },
      { to: '/inventory/transfers', label: 'إذون التحويل', icon: 'swap_horiz' },
      { to: '/inventory/shortages', label: 'النواقص والمرتجعات', icon: 'report', roles: ['admin'] },
    ],
  },
  {
    label: 'العمليات',
    roles: ['admin', 'staff'],
    items: [
      { to: '/partners', label: 'الوكلاء والفروع', icon: 'hub' },
      { to: '/production', label: 'أوامر التصنيع', icon: 'precision_manufacturing' },
      { to: '/logistics', label: 'اللوجستيات', icon: 'local_shipping' },
      { to: '/logistics/shipments', label: 'الشحنات', icon: 'inventory' },
      { to: '/logistics/deliver', label: 'تأكيد التسليم', icon: 'task_alt' },
      { to: '/pos/settle', label: 'تسوية نقطة البيع', icon: 'point_of_sale' },
    ],
  },
  {
    label: 'نقطة البيع',
    roles: ['agent', 'branch'],
    items: [
      { to: '/pos', label: 'نقطة البيع', icon: 'point_of_sale' },
      { to: '/pos/sales', label: 'مبيعاتي', icon: 'receipt_long' },
      { to: '/credit/payments', label: 'اعتماد السداد', icon: 'price_check' },
    ],
  },
  {
    label: 'المحادثات',
    roles: ['customer', 'supplier', 'admin', 'staff'],
    items: [{ to: '/chat', label: 'المحادثات', icon: 'forum' }],
  },
  {
    label: 'الإشعارات',
    roles: ['customer', 'supplier', 'agent', 'branch', 'admin', 'staff'],
    items: [{ to: '/notifications', label: 'مركز الإشعارات', icon: 'notifications' }],
  },
  {
    label: 'المورد',
    roles: ['supplier'],
    items: [
      { to: '/home', label: 'لوحة التحكم', icon: 'space_dashboard', end: true },
      { to: '/supplier/orders', label: 'طلبات واردة', icon: 'inbox' },
      { to: '/supplier/products', label: 'منتجاتي', icon: 'inventory_2' },
    ],
  },
  {
    label: 'السوق',
    roles: ['customer'],
    items: [
      { to: '/catalog', label: 'الكتالوج', icon: 'storefront' },
      { to: '/quick-order', label: 'طلب سريع', icon: 'bolt' },
      { to: '/cart', label: 'سلتي', icon: 'shopping_cart' },
      { to: '/orders', label: 'طلباتي', icon: 'list_alt' },
      { to: '/rfq', label: 'طلب عرض سعر', icon: 'request_quote' },
      { to: '/statement', label: 'كشف الحساب', icon: 'account_balance_wallet' },
      { to: '/pay/receipt', label: 'رفع إيصال تحويل', icon: 'upload_file' },
    ],
  },
  {
    label: 'حسابي',
    roles: ['customer', 'agent', 'branch'],
    items: [{ to: '/home', label: 'لوحة التحكم', icon: 'space_dashboard', end: true }],
  },
]

export function AppShell() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const role = user?.kind ?? 'customer'
  const perms = user?.permissions ?? []
  const hasPerm = (code?: string) => !code || perms.includes(code) || perms.includes('*')

  // T-35: show a bottom fade + down-chevron (with a «+N عناصر» count) while the
  // nav still has links below the fold, hiding it once scrolled to the bottom.
  const navRef = useRef<HTMLElement | null>(null)
  const [navScroll, setNavScroll] = useState({ before: false, after: false, below: 0 })
  useEffect(() => {
    const el = navRef.current
    if (!el) return
    const measure = () => {
      const before = el.scrollTop > 1
      const fold = el.scrollTop + el.clientHeight
      const after = fold < el.scrollHeight - 1
      let below = 0
      if (after) {
        el.querySelectorAll<HTMLElement>('a[href]').forEach((a) => {
          if (a.offsetTop >= fold - 4) below++
        })
      }
      setNavScroll((p) => (p.before === before && p.after === after && p.below === below ? p : { before, after, below }))
    }
    measure()
    el.addEventListener('scroll', measure, { passive: true })
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    window.addEventListener('resize', measure)
    return () => {
      el.removeEventListener('scroll', measure)
      ro.disconnect()
      window.removeEventListener('resize', measure)
    }
  }, [role, perms])

  // Auto-show the onboarding page on first login only: never if the user has
  // hidden it, never twice (a per-user 'seen' flag), and never blocking — it is
  // a one-time redirect. All storage access is guarded. Runs once per mount.
  const didAutoShow = useRef(false)
  useEffect(() => {
    if (didAutoShow.current || !user) return
    const path = location.pathname
    const isAuthRoute =
      path === '/login' || path === '/otp' || path.startsWith('/register')
    if (isAuthRoute) return
    didAutoShow.current = true
    try {
      const hidden = localStorage.getItem(`wm-onboarding-hidden-${user.id}`) === '1'
      const seen = localStorage.getItem(`wm-onboarding-seen-${user.id}`) === '1'
      if (!hidden && !seen) {
        localStorage.setItem(`wm-onboarding-seen-${user.id}`, '1')
        navigate('/start')
      }
    } catch {
      /* private mode / blocked storage — fine */
    }
  }, [user, location.pathname, navigate])

  const navItem = (active: boolean) =>
    `flex items-center gap-space-sm px-space-md py-2 rounded-lg font-body text-body transition-colors ${
      active
        ? 'bg-primary text-on-primary font-medium shadow-card-sm'
        : 'text-secondary hover:bg-surface-container-low hover:text-on-surface'
    }`

  async function onSignOut() {
    await signOut()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-surface">
      <aside className="fixed top-space-md bottom-space-md right-space-md w-[244px] z-40 bg-surface-container-lowest border border-surface-container-high rounded-2xl shadow-card flex flex-col select-none overflow-hidden">
        {/* Brand */}
        <div className="flex items-center gap-space-sm px-space-md pt-space-md pb-space-sm">
          <span
            className="w-9 h-9 rounded-xl grid place-items-center shrink-0"
            style={{ background: 'linear-gradient(145deg,#2b3a67,#141b35)' }}
          >
            <img src={logoUrl} alt="White Moon" width={24} height={24} style={{ width: 24, height: 24, objectFit: 'contain' }} />
          </span>
          <div className="flex flex-col leading-tight min-w-0">
            <b className="font-headline-2 text-headline-2 text-on-surface font-medium">وايت مون</b>
            <span className="font-mono-body text-[11px] text-secondary tracking-[0.15em]">WHITE MOON</span>
          </div>
        </div>

        {/* Nav */}
        <div className="relative flex-1 min-h-0">
        <nav ref={navRef} className="wm-scrollbar h-full overflow-y-auto px-space-sm pb-space-sm flex flex-col gap-space-xs">
          {/* Onboarding — first entry, every role, outside the role-gated groups */}
          <NavLink to="/start" className={({ isActive }) => navItem(isActive)}>
            <Icon name="rocket_launch" size={18} className="shrink-0" />
            <span className="flex-1 min-w-0 truncate">كيف أبدأ؟</span>
          </NavLink>
          {/* User guide — standalone full-page doc, every role */}
          <NavLink to="/guide" className={({ isActive }) => navItem(isActive)}>
            <Icon name="menu_book" size={18} className="shrink-0" />
            <span className="flex-1 min-w-0 truncate">دليل الاستخدام</span>
          </NavLink>
          {/* Change password — every role */}
          <NavLink to="/account/password" className={({ isActive }) => navItem(isActive)}>
            <Icon name="password" size={18} className="shrink-0" />
            <span className="flex-1 min-w-0 truncate">تغيير كلمة المرور</span>
          </NavLink>

          {GROUPS.filter((g) => g.roles.includes(role)).map((g) => (
            <div key={g.label} className="flex flex-col">
              <div className="px-space-md pt-space-sm pb-space-xs font-small text-[11px] text-on-surface-variant tracking-wider">
                {g.label}
              </div>
              {g.items
                .filter((it) => (!it.roles || it.roles.includes(role)) && hasPerm(it.perm))
                .map((it) => (
                  <NavLink key={it.to} to={it.to} end={it.end} className={({ isActive }) => navItem(isActive)}>
                    <Icon name={it.icon} size={18} className="shrink-0" />
                    <span className="flex-1 min-w-0 truncate">{it.label}</span>
                  </NavLink>
                ))}
            </div>
          ))}
        </nav>
        {navScroll.before && (
          <div className="pointer-events-none absolute inset-x-0 top-0 h-5 bg-gradient-to-b from-surface-container-lowest to-transparent" />
        )}
        {navScroll.after && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-col items-center">
            <div className="h-7 w-full bg-gradient-to-t from-surface-container-lowest to-transparent" />
            <div className="-mt-4 mb-1 flex items-center gap-1 rounded-full border border-surface-container-high bg-surface-container-high/95 px-2 py-0.5 font-small text-[11px] text-secondary">
              <Icon name="keyboard_arrow_down" size={14} />
              {navScroll.below > 0 && <span>+{navScroll.below} عناصر</span>}
            </div>
          </div>
        )}
        </div>

        {/* Account */}
        <div className="p-space-sm border-t border-surface-container-high">
          <button
            onClick={onSignOut}
            className="w-full flex items-center justify-between gap-space-sm px-space-sm py-space-xs rounded-lg hover:bg-surface-container-low transition-colors"
          >
            <span className="flex items-center gap-space-sm min-w-0">
              <span className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                <Icon name="person" size={18} className="text-on-primary" />
              </span>
              <span className="font-body-medium text-body-medium text-on-surface truncate">
                {user?.email ?? user?.phone ?? 'حسابي'}
              </span>
            </span>
            <Icon name="logout" size={18} className="text-secondary shrink-0" />
          </button>
        </div>
      </aside>

      <div className="mr-[276px]">
        <ImpersonationBanner />
        {role === 'customer' && <CustomerCreditBar />}
        <main className="max-w-[1040px] mx-auto pt-[40px] px-[32px] pb-[96px] min-h-screen">
          <Outlet />
        </main>
      </div>
      {/* Admin AI assistant dock — self-gates to admins, carries the current route */}
      <AssistantWidget />
    </div>
  )
}

const CREDIT_TIER_AR: Record<string, string> = { green: 'أخضر', white: 'أبيض', yellow: 'أصفر', red: 'أحمر' }

/** T-45: always-on balance bar for customers — available deferred headroom,
 *  limit, and tier. Silent on failure (never blocks the shell). */
function CustomerCreditBar() {
  const [c, setC] = useState<MyCredit | null>(null)
  useEffect(() => {
    let active = true
    getMyCredit().then((d) => { if (active) setC(d) }).catch(() => { /* non-blocking */ })
    return () => { active = false }
  }, [])
  if (!c) return null
  const blocked = c.tier === 'red' || Number(c.available) <= 0
  return (
    <div className={`w-full px-[32px] py-2 border-b border-surface-container-high flex flex-wrap items-center justify-center gap-space-sm font-small text-small ${blocked ? 'bg-warning/10 text-on-surface' : 'bg-surface-container-low text-secondary'}`}>
      <span>
        المتاح لك للأجل{' '}
        <bdi dir="ltr" className="font-mono-medium text-primary">{formatMoney(c.available)}</bdi>{' '}
        من{' '}
        <bdi dir="ltr" className="font-mono-medium">{formatMoney(c.effective_limit)}</bdi> ج.م
      </span>
      <span>— تصنيفك: {CREDIT_TIER_AR[c.tier] ?? c.tier}</span>
      {c.order_block_level >= 4 && <span className="text-danger">الطلبات موقوفة حتى تسوية المتأخرات</span>}
    </div>
  )
}

/** Centered reading/form column (760px) used by most pages. */
export function Narrow({ children }: { children: ReactNode }) {
  return <div className="w-full max-w-[760px] mx-auto">{children}</div>
}

/** Wide column (1040px) for dense tables — the shell already caps at 1040. */
export function Wide({ children }: { children: ReactNode }) {
  return <div className="w-full">{children}</div>
}

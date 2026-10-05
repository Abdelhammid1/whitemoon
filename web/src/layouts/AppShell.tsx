import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'
import { Icon } from '../components/Icon'
import { ImpersonationBanner } from '../components/ImpersonationBanner'

interface NavEntry {
  to: string
  label: string
  icon: string
  end?: boolean
  /** Optional per-item gate, narrower than the group's roles. */
  roles?: string[]
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
      { to: '/', label: 'لوحة التحكم', icon: 'space_dashboard', end: true },
      { to: '/dashboard', label: 'التحليلات التنفيذية', icon: 'monitoring' },
      { to: '/admin/users', label: 'المستخدمون', icon: 'group' },
      { to: '/admin/suppliers/pending', label: 'الموردون المعلقون', icon: 'how_to_reg' },
      { to: '/admin/audit', label: 'سجل التدقيق', icon: 'history' },
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
      { to: '/compliance', label: 'جاهزية ETA', icon: 'verified' },
    ],
  },
  {
    label: 'المستودع',
    roles: ['admin', 'staff'],
    items: [
      { to: '/inventory/products', label: 'المنتجات والمخزون', icon: 'inventory_2' },
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
      { to: '/', label: 'لوحة التحكم', icon: 'space_dashboard', end: true },
      { to: '/supplier/orders', label: 'طلبات واردة', icon: 'inbox' },
      { to: '/inventory/offers', label: 'عروضي', icon: 'sell' },
      { to: '/inventory/stock', label: 'مخزوني', icon: 'warehouse' },
    ],
  },
  {
    label: 'السوق',
    roles: ['customer'],
    items: [
      { to: '/catalog', label: 'الكتالوج', icon: 'storefront' },
      { to: '/cart', label: 'سلتي', icon: 'shopping_cart' },
      { to: '/orders', label: 'طلباتي', icon: 'list_alt' },
      { to: '/rfq', label: 'طلب عرض سعر', icon: 'request_quote' },
    ],
  },
  {
    label: 'حسابي',
    roles: ['customer', 'agent', 'branch'],
    items: [{ to: '/', label: 'لوحة التحكم', icon: 'space_dashboard', end: true }],
  },
]

export function AppShell() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const role = user?.kind ?? 'customer'

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
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path d="M15.5 2a10 10 0 1 0 6.5 17.3A8 8 0 0 1 15.5 2Z" className="text-gold" fill="currentColor" />
            </svg>
          </span>
          <div className="flex flex-col leading-tight min-w-0">
            <b className="font-headline-2 text-headline-2 text-on-surface font-medium">وايت مون</b>
            <span className="font-mono-body text-[11px] text-secondary tracking-[0.15em]">WHITE MOON</span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-space-sm pb-space-sm flex flex-col gap-space-xs">
          {GROUPS.filter((g) => g.roles.includes(role)).map((g) => (
            <div key={g.label} className="flex flex-col">
              <div className="px-space-md pt-space-sm pb-space-xs font-small text-[11px] text-on-surface-variant tracking-wider">
                {g.label}
              </div>
              {g.items
                .filter((it) => !it.roles || it.roles.includes(role))
                .map((it) => (
                  <NavLink key={it.to} to={it.to} end={it.end} className={({ isActive }) => navItem(isActive)}>
                    <Icon name={it.icon} size={18} className="shrink-0" />
                    <span className="flex-1 min-w-0 truncate">{it.label}</span>
                  </NavLink>
                ))}
            </div>
          ))}
        </nav>

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
        <main className="max-w-[1040px] mx-auto pt-[40px] px-[32px] pb-[96px] min-h-screen">
          <Outlet />
        </main>
      </div>
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

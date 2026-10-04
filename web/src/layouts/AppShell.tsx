import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'
import { Brand } from '../components/Brand'
import { Icon } from '../components/Icon'
import { ImpersonationBanner } from '../components/ImpersonationBanner'

interface NavEntry {
  to: string
  label: string
  end?: boolean
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
      { to: '/', label: 'لوحة التحكم', end: true },
      { to: '/admin/users', label: 'المستخدمون' },
      { to: '/admin/suppliers/pending', label: 'الموردون المعلقون' },
      { to: '/admin/audit', label: 'سجل التدقيق' },
      { to: '/admin/impersonation', label: 'الدخول كمستخدم' },
    ],
  },
  {
    label: 'المالية',
    roles: ['admin', 'staff'],
    items: [
      { to: '/accounting/chart', label: 'دليل الحسابات' },
      { to: '/accounting/periods', label: 'الفترات المالية' },
      { to: '/accounting/journal/manual', label: 'قيد يدوي' },
      { to: '/accounting/receipts', label: 'الإيصالات والعمليات' },
      { to: '/accounting/deferred', label: 'البيع الآجل' },
      { to: '/accounting/reports', label: 'التقارير' },
    ],
  },
  {
    label: 'المستودع',
    roles: ['admin', 'staff'],
    items: [
      { to: '/inventory/products', label: 'المنتجات والمخزون' },
      { to: '/inventory/stock', label: 'أرصدة المخزون' },
      { to: '/inventory/transfers', label: 'إذون التحويل' },
      { to: '/inventory/shortages', label: 'النواقص والمرتجعات' },
    ],
  },
  {
    label: 'المورد',
    roles: ['supplier'],
    items: [
      { to: '/', label: 'لوحة التحكم', end: true },
      { to: '/inventory/offers', label: 'عروضي' },
      { to: '/inventory/stock', label: 'مخزوني' },
    ],
  },
  {
    label: 'السوق',
    roles: ['customer'],
    items: [
      { to: '/catalog', label: 'الكتالوج' },
      { to: '/cart', label: 'سلتي' },
      { to: '/orders', label: 'طلباتي' },
      { to: '/rfq', label: 'طلب عرض سعر' },
    ],
  },
  {
    label: 'حسابي',
    roles: ['customer', 'agent', 'branch'],
    items: [{ to: '/', label: 'لوحة التحكم', end: true }],
  },
]

export function AppShell() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const role = user?.kind ?? 'customer'

  const navItem = (active: boolean) =>
    `px-space-lg py-1.5 font-body text-body transition-colors border-r-2 ${
      active
        ? 'text-primary font-medium border-primary'
        : 'text-secondary hover:text-primary border-transparent'
    }`

  async function onSignOut() {
    await signOut()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-surface-container-lowest">
      <aside className="fixed top-0 right-0 h-screen w-[224px] bg-surface-container-lowest border-l border-surface-container-highest z-40 flex flex-col justify-between select-none">
        <div className="flex flex-col overflow-y-auto">
          <div className="h-16 px-space-lg flex items-center border-b border-surface-container-highest">
            <Brand size={24} />
          </div>
          <nav className="flex flex-col pt-space-md pb-space-md">
            {GROUPS.filter((g) => g.roles.includes(role)).map((g) => (
              <div key={g.label} className="flex flex-col">
                <div className="px-space-lg pt-space-md pb-space-xs font-small text-small text-secondary tracking-wider">
                  {g.label}
                </div>
                {g.items.map((it) => (
                  <NavLink
                    key={it.to}
                    to={it.to}
                    end={it.end}
                    className={({ isActive }) => navItem(isActive)}
                  >
                    {it.label}
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
        </div>

        <div className="p-space-md border-t border-surface-container-highest">
          <button
            onClick={onSignOut}
            className="w-full flex items-center justify-between px-space-xs py-space-xs text-on-surface hover:text-primary transition-colors"
          >
            <span className="flex items-center gap-space-sm min-w-0">
              <span className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                <Icon name="person" size={18} className="text-on-primary" />
              </span>
              <span className="font-body-medium text-body-medium text-primary truncate">
                {user?.email ?? user?.phone ?? 'حسابي'}
              </span>
            </span>
            <Icon name="logout" size={18} className="text-secondary" />
          </button>
        </div>
      </aside>

      <div className="mr-[224px]">
        <ImpersonationBanner />
        <main className="max-w-[1040px] mx-auto pt-[48px] px-[32px] pb-[96px] min-h-screen">
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

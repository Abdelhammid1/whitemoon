import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { Brand } from '../components/Brand'

/**
 * Two-pane layout from DESIGN.md: fixed ~260px right-side sidebar (RTL),
 * centered main content capped at 900px. Everything flat.
 */
export function AppShell() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const navItem =
    'flex items-center gap-2 rounded-xl px-3 py-2 text-body text-graphite hover:text-ink'
  const activeItem = 'bg-deep-teal text-parchment hover:text-parchment'

  const canSeeAdmin = user && (user.kind === 'admin' || user.kind === 'staff')
  const canSeeAccounting = user && (user.kind === 'admin' || user.kind === 'staff')

  async function onSignOut() {
    await signOut()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-parchment text-ink">
      <aside
        className="fixed inset-y-0 end-0 w-[260px] border-s border-warm-mist bg-parchment px-3 py-6"
        aria-label="القائمة الجانبية"
      >
        <div className="mb-6 px-3">
          <Brand size={24} />
        </div>

        <div className="flex flex-col gap-1">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `${navItem} ${isActive ? activeItem : ''}`}
          >
            <span>الصفحة الرئيسية</span>
          </NavLink>

          {canSeeAccounting && (
            <>
              <p className="mt-4 px-3 text-body-sm text-graphite">المحاسبة</p>
              <NavLink
                to="/accounting/periods"
                className={({ isActive }) => `${navItem} ${isActive ? activeItem : ''}`}
              >
                الفترات المحاسبية
              </NavLink>
              <NavLink
                to="/accounting/journal/manual"
                className={({ isActive }) => `${navItem} ${isActive ? activeItem : ''}`}
              >
                قيد يدوي
              </NavLink>
              <NavLink
                to="/accounting/receipts"
                className={({ isActive }) => `${navItem} ${isActive ? activeItem : ''}`}
              >
                إيصالات التحصيل
              </NavLink>
              <NavLink
                to="/accounting/deferred"
                className={({ isActive }) => `${navItem} ${isActive ? activeItem : ''}`}
              >
                الآجل والخصم المبكر
              </NavLink>
              <NavLink
                to="/accounting/reports/trial-balance"
                className={({ isActive }) => `${navItem} ${isActive ? activeItem : ''}`}
              >
                التقارير
              </NavLink>
            </>
          )}

          {canSeeAdmin && (
            <>
              <p className="mt-4 px-3 text-body-sm text-graphite">الإدارة</p>
              <NavLink
                to="/admin/users"
                className={({ isActive }) => `${navItem} ${isActive ? activeItem : ''}`}
              >
                المستخدمون
              </NavLink>
              <NavLink
                to="/admin/suppliers/pending"
                className={({ isActive }) => `${navItem} ${isActive ? activeItem : ''}`}
              >
                الموردون قيد الاعتماد
              </NavLink>
              <NavLink
                to="/admin/impersonation"
                className={({ isActive }) => `${navItem} ${isActive ? activeItem : ''}`}
              >
                الدخول كمستخدم
              </NavLink>
            </>
          )}
        </div>

        <div className="absolute inset-x-3 bottom-6">
          <div className="mb-2 flex items-center justify-between gap-2">
            <span className="text-body-sm text-graphite truncate">
              {user?.email ?? user?.phone ?? 'ضيف'}
            </span>
            {user && <Badge tone="neutral">{roleLabel(user.kind)}</Badge>}
          </div>
          <Button className="w-full" onClick={onSignOut}>
            تسجيل الخروج
          </Button>
        </div>
      </aside>

      <main className="pe-[260px]">
        <div className="mx-auto max-w-[900px] px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

function roleLabel(kind: string): string {
  switch (kind) {
    case 'admin':
      return 'مدير'
    case 'staff':
      return 'موظف'
    case 'customer':
      return 'عميل'
    case 'supplier':
      return 'مورد'
    case 'agent':
      return 'وكيل'
    case 'branch':
      return 'فرع'
    default:
      return kind
  }
}

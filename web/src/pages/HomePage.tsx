import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Narrow } from '../layouts/AppShell'
import { Dot, Pill } from '../components/ui'
import { useAuth } from '../auth/AuthContext'
import { listPendingSuppliers } from '../api/admin'

const QUICK_LINKS_ADMIN = [
  { to: '/accounting/journal/manual', label: 'إنشاء قيد محاسبي يدوي' },
  { to: '/admin/suppliers/pending', label: 'مراجعة واعتماد الموردين المعلقين' },
  { to: '/accounting/chart', label: 'استعراض دليل الحسابات الموحد' },
  { to: '/accounting/reports', label: 'التقارير المالية' },
]
const QUICK_LINKS_SUPPLIER = [
  { to: '/inventory/offers', label: 'إدارة عروضي التوريدية' },
  { to: '/inventory/stock', label: 'استعراض مخزوني' },
]

function cairoToday(): string {
  try {
    return new Intl.DateTimeFormat('ar-EG', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }).format(new Date())
  } catch {
    return ''
  }
}

export function HomePage() {
  const { user } = useAuth()
  const [pendingCount, setPendingCount] = useState<number | null>(null)
  const isAdmin = user?.kind === 'admin' || user?.kind === 'staff'

  useEffect(() => {
    if (!isAdmin) return
    listPendingSuppliers()
      .then((r) => setPendingCount(r.items.length))
      .catch(() => setPendingCount(null))
  }, [isAdmin])

  if (!user) return null
  const name = user.email ?? user.phone ?? ''
  const links = user.kind === 'supplier' ? QUICK_LINKS_SUPPLIER : QUICK_LINKS_ADMIN

  return (
    <Narrow>
      <header className="flex flex-col">
        <h1 className="font-display text-display text-primary font-medium tracking-tight">
          أهلاً بك في وايت مون
        </h1>
        <p className="font-body text-body text-secondary mt-space-xs">
          ملخص العمليات والروابط المباشرة لنظام وايت مون
        </p>
      </header>

      {isAdmin && (
        <section className="mt-[48px] flex flex-col">
          <div className="flex items-baseline justify-between pb-space-sm border-b border-surface-container-highest">
            <h2 className="font-headline-1 text-headline-1 text-primary font-medium">اليوم</h2>
            <span className="font-mono-body text-mono-body text-secondary">
              <bdi dir="rtl">{cairoToday()}</bdi>
            </span>
          </div>
          <div className="flex flex-col divide-y divide-surface-container-highest">
            {pendingCount === null ? (
              <p className="py-space-md font-body text-body text-secondary">جار التحميل…</p>
            ) : pendingCount === 0 ? (
              <p className="py-space-md font-body text-body text-secondary">لا توجد مهام عاجلة اليوم.</p>
            ) : (
              <Link
                to="/admin/suppliers/pending"
                className="py-space-md flex items-center justify-between gap-space-sm hover:bg-surface transition-colors px-space-xs -mx-space-xs rounded"
              >
                <span className="flex items-center gap-space-md min-w-0">
                  <Dot tone="warning" />
                  <span className="font-body-medium text-body-medium text-on-surface truncate">
                    {pendingCount} طلبات اعتماد موردين تنتظر مراجعة السجل التجاري
                  </span>
                </span>
                <Pill tone="warning">قيد المراجعة</Pill>
              </Link>
            )}
          </div>
        </section>
      )}

      <section className="mt-[48px] flex flex-col">
        <div className="pb-space-sm border-b border-surface-container-highest">
          <h3 className="font-headline-2 text-headline-2 text-primary font-medium">روابط سريعة</h3>
        </div>
        <nav className="flex flex-col divide-y divide-surface-container-highest">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className="py-space-md flex items-center justify-between group px-space-xs -mx-space-xs hover:bg-surface rounded transition-colors"
            >
              <span className="font-body text-body text-primary group-hover:underline underline-offset-4 decoration-1 decoration-outline">
                {l.label}
              </span>
              <span className="font-mono-body text-mono-body text-secondary group-hover:text-primary">↗</span>
            </Link>
          ))}
        </nav>
      </section>

      <p className="mt-[48px] font-small text-small text-secondary">
        {name}
      </p>
    </Narrow>
  )
}

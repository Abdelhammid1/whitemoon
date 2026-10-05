import { Link } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Card } from '../../components/ui'
import { Icon } from '../../components/Icon'

const REPORTS = [
  { to: '/accounting/reports/trial-balance', title: 'ميزان المراجعة', desc: 'أرصدة كل الحسابات لفترة محددة مع التحقق من التوازن.', icon: 'balance' },
  { to: '/accounting/reports/income-statement', title: 'قائمة الدخل', desc: 'الإيرادات والمصروفات وصافي الدخل للفترة.', icon: 'trending_up' },
  { to: '/accounting/reports/balance-sheet', title: 'المركز المالي', desc: 'الأصول والالتزامات وحقوق الملكية كما في تاريخ.', icon: 'account_balance' },
  { to: '/accounting/reports/cash-flow', title: 'التدفقات النقدية', desc: 'مصادر واستخدامات النقد وصافي التغير.', icon: 'payments' },
  { to: '/accounting/reports/general-ledger', title: 'الأستاذ العام', desc: 'حركة حساب واحد مع الرصيد الجاري.', icon: 'menu_book' },
]

export function ReportsIndexPage() {
  return (
    <Wide>
      <PageTitle title="التقارير المالية" subtitle="تُستخرج مباشرة من شجرة الحسابات — كل القيم بالجنيه المصري." />

      <nav className="mt-space-xl grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-space-md">
        {REPORTS.map((r) => (
          <Link key={r.to} to={r.to} className="group">
            <Card
              padded={false}
              className="h-full p-space-lg flex flex-col gap-space-md transition-shadow group-hover:shadow-overlay"
            >
              <div className="flex items-start justify-between">
                <span className="w-10 h-10 rounded-xl bg-brand-weak flex items-center justify-center shrink-0">
                  <Icon name={r.icon} size={20} className="text-primary" />
                </span>
                <Icon name="arrow_back" size={18} className="text-outline group-hover:text-primary transition-colors" />
              </div>
              <div className="flex flex-col gap-space-xs">
                <span className="font-body-medium text-body-medium text-on-surface">{r.title}</span>
                <span className="font-small text-small text-secondary">{r.desc}</span>
              </div>
            </Card>
          </Link>
        ))}
      </nav>
    </Wide>
  )
}

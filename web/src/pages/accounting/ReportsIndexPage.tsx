import { Link } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle } from '../../components/ui'

const REPORTS = [
  { to: '/accounting/reports/trial-balance', title: 'ميزان المراجعة', desc: 'أرصدة كل الحسابات لفترة محددة مع التحقق من التوازن.' },
  { to: '/accounting/reports/income-statement', title: 'قائمة الدخل', desc: 'الإيرادات والمصروفات وصافي الدخل للفترة.' },
  { to: '/accounting/reports/balance-sheet', title: 'المركز المالي', desc: 'الأصول والالتزامات وحقوق الملكية كما في تاريخ.' },
  { to: '/accounting/reports/cash-flow', title: 'التدفقات النقدية', desc: 'مصادر واستخدامات النقد وصافي التغير.' },
  { to: '/accounting/reports/general-ledger', title: 'الأستاذ العام', desc: 'حركة حساب واحد مع الرصيد الجاري.' },
]

export function ReportsIndexPage() {
  return (
    <Narrow>
      <PageTitle title="التقارير المالية" subtitle="تُستخرج مباشرة من شجرة الحسابات." />
      <nav className="mt-space-xl flex flex-col divide-y divide-surface-container-highest">
        {REPORTS.map((r) => (
          <Link key={r.to} to={r.to} className="py-space-md flex items-center justify-between group px-space-xs -mx-space-xs hover:bg-surface rounded transition-colors">
            <span className="flex flex-col">
              <span className="font-body-medium text-body-medium text-primary group-hover:underline underline-offset-4 decoration-1 decoration-outline">{r.title}</span>
              <span className="font-small text-small text-secondary mt-0.5">{r.desc}</span>
            </span>
            <span className="font-mono-body text-mono-body text-secondary group-hover:text-primary">↗</span>
          </Link>
        ))}
      </nav>
    </Narrow>
  )
}

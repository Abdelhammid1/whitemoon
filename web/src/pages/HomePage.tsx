import { Link } from 'react-router-dom'
import { Card, CardHeader } from '../components/Card'
import { useAuth } from '../auth/AuthContext'
import { Badge } from '../components/Badge'

export function HomePage() {
  const { user } = useAuth()
  if (!user) return null

  return (
    <div className="flex flex-col gap-8">
      <section>
        <h1 className="text-body-lg text-ink">أهلاً بك في وايت مون</h1>
        <p className="mt-1 text-body text-graphite">
          لوحة التحكم المتكاملة — إدارة الحسابات والعملاء والموردين والمخزون.
        </p>
      </section>

      <section className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Link to="/accounting/reports/trial-balance" className="block">
          <Card elevated>
            <CardHeader
              title="ميزان المراجعة"
              subtitle="عرض أرصدة الحسابات لفترة محددة"
            />
            <p className="text-body text-graphite">
              الدخول السريع لتقرير الـTB بفلاتر زمنية.
            </p>
          </Card>
        </Link>
        <Link to="/accounting/periods" className="block">
          <Card elevated>
            <CardHeader
              title="الفترات المحاسبية"
              subtitle="فتح وإقفال الفترات الشهرية"
            />
            <p className="text-body text-graphite">
              إنشاء الفترات، إقفالها، أو إعادة فتحها بصلاحية الإدارة العليا.
            </p>
          </Card>
        </Link>
        <Link to="/admin/suppliers/pending" className="block">
          <Card elevated>
            <CardHeader
              title="الموردون قيد الاعتماد"
              subtitle="مراجعة ملفات التأهيل"
            />
            <p className="text-body text-graphite">
              اعتماد أو رفض حسابات الموردين الجديدة.
            </p>
          </Card>
        </Link>
        <Link to="/accounting/receipts" className="block">
          <Card elevated>
            <CardHeader
              title="إيصالات التحصيل (OCR)"
              subtitle="مطابقة التحويلات البنكية"
            />
            <p className="text-body text-graphite">
              رفع صور الإيصالات ومتابعة المطابقة التلقائية.
            </p>
          </Card>
        </Link>
      </section>

      <section>
        <Card>
          <CardHeader title="حسابك" />
          <div className="flex flex-wrap items-center gap-3 text-body text-ink">
            <Badge tone="neutral">{user.kind}</Badge>
            <Badge tone="muted">{user.status}</Badge>
            <span className="text-graphite">
              {user.email ?? user.phone ?? '—'}
            </span>
          </div>
        </Card>
      </section>
    </div>
  )
}

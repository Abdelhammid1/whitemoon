import { Link } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { Button } from '../components/ui'
import { Icon } from '../components/Icon'

/**
 * Public marketing landing page — same "Nightfall" system as the app
 * (navy #2b3a67 + moonlight-gold #a8812b, IBM Plex Sans Arabic, RTL).
 * Standalone (outside AppShell) with its own header/footer; links into the
 * real /login and /register flows.
 */

function NavAccent({ children }: { children: string }) {
  return <span className="text-tertiary-fixed">{children}</span>
}

const VALUE_PROPS = [
  {
    icon: 'visibility_off',
    title: 'سوق وسيط يحمي الهويات',
    body: 'المورّد لا يظهر للعميل أبدًا، والعميل لا يظهر للمورّد. الشركة تتوسّط كل صفقة ومحادثة.',
  },
  {
    icon: 'payments',
    title: 'بيع آجل محسوب على الخادم',
    body: 'سعر نقدي وآجل وخصم سداد مبكر، محسوبة آليًا للقراءة فقط — بلا اجتهاد يدوي.',
  },
  {
    icon: 'account_balance',
    title: 'محاسبة ومخزون متكاملان',
    body: 'قيود مزدوجة، فترات مالية، تصنيف ائتماني، لوجستيات وفواتير — نظام واحد بالعربي.',
  },
  {
    icon: 'language',
    title: 'عربي أولًا، بالجنيه المصري',
    body: 'واجهة RTL كاملة بالجنيه المصري (ج.م)، مصمّمة لسوق الجملة في مصر.',
  },
]

const ROLES = [
  {
    icon: 'storefront',
    title: 'للعملاء (تجّار التجزئة)',
    points: ['تصفّح الكتالوج بأفضل سعر', 'سقف ائتماني وبيع آجل', 'حجز مواعيد التوصيل وتتبّع الشحنة'],
    cta: { to: '/register', label: 'حساب عميل جديد' },
  },
  {
    icon: 'inventory_2',
    title: 'للمورّدين',
    points: ['عروض أسعار على المنتجات', 'إنبوكس طلبات عروض الأسعار', 'إدارة المخزون وحد إعادة الطلب'],
    cta: { to: '/register/supplier', label: 'تسجيل كمورد تجاري' },
  },
  {
    icon: 'hub',
    title: 'للوكلاء والفروع',
    points: ['نقطة بيع بعمولة مُسجّلة', 'نطاق جغرافي محدّد', 'متابعة المبيعات والتحصيل'],
    cta: { to: '/login', label: 'تسجيل الدخول' },
  },
]

const FEATURES = [
  { icon: 'search', label: 'كتالوج ذكي' },
  { icon: 'request_quote', label: 'طلبات عروض الأسعار' },
  { icon: 'credit_score', label: 'التصنيف الائتماني' },
  { icon: 'local_shipping', label: 'تتبّع الشحنات' },
  { icon: 'receipt_long', label: 'فواتير بالعربي' },
  { icon: 'summarize', label: 'تقارير مالية' },
  { icon: 'forum', label: 'محادثة وسيطة' },
  { icon: 'verified', label: 'جاهزية ETA' },
]

const STEPS = [
  { n: '١', title: 'سجّل حسابك', body: 'عميل أو مورّد — بتفعيل تحقّق ثنائي وبيانات متجرك.' },
  { n: '٢', title: 'ابدأ التعامل', body: 'تصفّح، اطلب عرض سعر، أضف للسلة، أو انشر عروضك.' },
  { n: '٣', title: 'تابع كل شيء', body: 'طلبات وشحنات وذمم وتحصيل — في لوحة واحدة.' },
]

export function LandingPage() {
  return (
    <div dir="rtl" className="min-h-screen bg-background text-on-surface font-body">
      {/* ── Header ───────────────────────────────────────────────── */}
      <header className="sticky top-0 z-20 border-b border-surface-container-high bg-background/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-space-md px-gutter py-space-sm">
          <Brand size={26} />
          <nav className="hidden items-center gap-space-lg font-small-medium text-small-medium text-on-surface-variant md:flex">
            <a href="#value" className="transition-colors hover:text-primary">المزايا</a>
            <a href="#roles" className="transition-colors hover:text-primary">لمن المنصة</a>
            <a href="#how" className="transition-colors hover:text-primary">كيف تعمل</a>
          </nav>
          <div className="flex items-center gap-space-sm">
            <Link to="/login"><Button variant="secondary">دخول</Button></Link>
            <Link to="/register" className="hidden sm:block">
              <Button variant="primary" iconRight="arrow_back">إنشاء حساب</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ─────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div className="mx-auto max-w-6xl px-gutter py-space-xl md:py-16">
          <div className="relative overflow-hidden rounded-2xl bg-primary px-space-lg py-12 text-on-primary shadow-card md:px-16 md:py-20">
            {/* moonlight glow + crescent */}
            <div aria-hidden className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-tertiary/20 blur-3xl" />
            <div aria-hidden className="pointer-events-none absolute -bottom-20 left-10 h-56 w-56 rounded-full bg-inverse-primary/10 blur-3xl" />
            <svg aria-hidden viewBox="0 0 24 24" className="absolute left-8 top-8 h-16 w-16 opacity-80 md:h-24 md:w-24" fill="none">
              <path d="M15.5 2a10 10 0 1 0 6.5 17.3A8 8 0 0 1 15.5 2Z" className="fill-tertiary-fixed-dim" />
            </svg>

            <div className="relative max-w-2xl">
              <span className="inline-flex items-center gap-space-xs rounded-pill bg-tertiary/20 px-space-md py-space-xs font-small-medium text-small-medium text-tertiary-fixed">
                <Icon name="nights_stay" size={16} /> سوق الجملة الذكي في مصر
              </span>
              <h1 className="mt-space-lg font-display text-[34px] font-semibold leading-tight tracking-tight md:text-[52px] md:leading-[1.1]">
                وايت مون — منصّة <NavAccent>B2B</NavAccent> متكاملة
                <br className="hidden sm:block" /> للتجارة والتوريد والمحاسبة
              </h1>
              <p className="mt-space-md max-w-xl font-body text-body text-on-primary/80 md:text-[17px] md:leading-8">
                سوق وسيط يحمي هوية المورّد والعميل، ببيع آجل محسوب آليًا، ونظام محاسبة ومخزون
                ولوجستيات كامل — كله بالعربي وبالجنيه المصري.
              </p>
              <div className="mt-space-xl flex flex-wrap items-center gap-space-md">
                <Link to="/register">
                  <Button variant="primary" iconRight="arrow_back"
                    className="!bg-tertiary !text-on-tertiary hover:!bg-[#8f6d22] !shadow-card">
                    ابدأ كعميل
                  </Button>
                </Link>
                <Link to="/register/supplier">
                  <Button className="!bg-transparent !border-on-primary/30 !text-on-primary hover:!bg-on-primary/10">
                    انضم كمورّد
                  </Button>
                </Link>
              </div>
              <div className="mt-space-xl flex flex-wrap gap-x-space-xl gap-y-space-sm font-small-medium text-small-medium text-on-primary/70">
                <span className="inline-flex items-center gap-space-xs"><Icon name="shield" size={16} className="text-tertiary-fixed-dim" /> هويات محمية</span>
                <span className="inline-flex items-center gap-space-xs"><Icon name="payments" size={16} className="text-tertiary-fixed-dim" /> بيع آجل محسوب</span>
                <span className="inline-flex items-center gap-space-xs"><Icon name="translate" size={16} className="text-tertiary-fixed-dim" /> عربي RTL كامل</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Value props ──────────────────────────────────────────── */}
      <section id="value" className="mx-auto max-w-6xl px-gutter py-space-xl">
        <SectionHead eyebrow="لماذا وايت مون" title="بُنيت لسوق الجملة، لا مكيّفة له" />
        <div className="mt-space-xl grid grid-cols-1 gap-space-md sm:grid-cols-2 lg:grid-cols-4">
          {VALUE_PROPS.map((v) => (
            <article key={v.title} className="flex flex-col gap-space-sm rounded-2xl border border-surface-container-high bg-surface-container-lowest p-space-lg shadow-card-sm transition-shadow hover:shadow-card">
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-brand-weak text-primary">
                <Icon name={v.icon} size={22} />
              </span>
              <h3 className="font-headline-2 text-headline-2 text-on-surface">{v.title}</h3>
              <p className="font-body text-body text-on-surface-variant">{v.body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ── Roles ────────────────────────────────────────────────── */}
      <section id="roles" className="bg-surface-container-low py-space-xl">
        <div className="mx-auto max-w-6xl px-gutter">
          <SectionHead eyebrow="لمن المنصّة" title="دور واضح لكل طرف في السوق" />
          <div className="mt-space-xl grid grid-cols-1 gap-space-md md:grid-cols-3">
            {ROLES.map((r) => (
              <article key={r.title} className="flex flex-col gap-space-md rounded-2xl border border-surface-container-high bg-surface-container-lowest p-space-lg shadow-card-sm">
                <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-gold-weak text-tertiary">
                  <Icon name={r.icon} size={24} />
                </span>
                <h3 className="font-headline-1 text-headline-1 text-primary">{r.title}</h3>
                <ul className="flex flex-col gap-space-sm">
                  {r.points.map((p) => (
                    <li key={p} className="flex items-start gap-space-sm font-body text-body text-on-surface-variant">
                      <Icon name="check_circle" size={18} className="mt-0.5 shrink-0 text-signal" />
                      <span>{p}</span>
                    </li>
                  ))}
                </ul>
                <Link to={r.cta.to} className="mt-auto pt-space-sm">
                  <Button variant="secondary" iconRight="arrow_back" className="w-full">{r.cta.label}</Button>
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────── */}
      <section id="how" className="mx-auto max-w-6xl px-gutter py-space-xl">
        <SectionHead eyebrow="كيف تعمل" title="ثلاث خطوات للبدء" />
        <div className="mt-space-xl grid grid-cols-1 gap-space-md md:grid-cols-3">
          {STEPS.map((s) => (
            <article key={s.n} className="relative rounded-2xl border border-surface-container-high bg-surface-container-lowest p-space-lg shadow-card-sm">
              <span className="font-display text-[40px] font-semibold leading-none text-tertiary/35">{s.n}</span>
              <h3 className="mt-space-sm font-headline-2 text-headline-2 text-on-surface">{s.title}</h3>
              <p className="mt-space-xs font-body text-body text-on-surface-variant">{s.body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ── Feature grid ─────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-gutter pb-space-xl">
        <div className="rounded-2xl border border-surface-container-high bg-surface-container-lowest p-space-lg shadow-card-sm md:p-space-xl">
          <h2 className="font-headline-1 text-headline-1 text-primary">كل أدوات التشغيل في مكان واحد</h2>
          <div className="mt-space-lg grid grid-cols-2 gap-space-md sm:grid-cols-4">
            {FEATURES.map((f) => (
              <div key={f.label} className="flex items-center gap-space-sm rounded-xl bg-surface-container-low px-space-md py-space-sm">
                <Icon name={f.icon} size={20} className="text-primary" />
                <span className="font-small-medium text-small-medium text-on-surface">{f.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA band ─────────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-gutter pb-space-xl">
        <div className="relative overflow-hidden rounded-2xl bg-inverse-surface px-space-lg py-12 text-inverse-on-surface shadow-card md:px-16">
          <div aria-hidden className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-tertiary/20 blur-3xl" />
          <div className="relative flex flex-col items-start justify-between gap-space-lg md:flex-row md:items-center">
            <div>
              <h2 className="font-display text-[26px] font-semibold tracking-tight md:text-[32px]">جاهز تبدأ التعامل؟</h2>
              <p className="mt-space-xs font-body text-body text-inverse-on-surface/75">أنشئ حسابك خلال دقائق وابدأ البيع أو الشراء اليوم.</p>
            </div>
            <div className="flex flex-wrap gap-space-md">
              <Link to="/register">
                <Button className="!bg-tertiary !text-on-tertiary hover:!bg-[#8f6d22] !shadow-card" iconRight="arrow_back">إنشاء حساب</Button>
              </Link>
              <Link to="/login">
                <Button className="!bg-transparent !border-inverse-on-surface/30 !text-inverse-on-surface hover:!bg-inverse-on-surface/10">تسجيل الدخول</Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────── */}
      <footer className="border-t border-surface-container-high">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-space-md px-gutter py-space-lg md:flex-row">
          <Brand size={22} />
          <p className="font-small text-small text-on-surface-variant">جميع الأسعار بالجنيه المصري (ج.م) · منصّة أعمال B2B</p>
          <div className="flex items-center gap-space-md font-small-medium text-small-medium text-on-surface-variant">
            <Link to="/login" className="hover:text-primary">دخول</Link>
            <span className="text-outline-variant">·</span>
            <Link to="/register" className="hover:text-primary">عميل جديد</Link>
            <span className="text-outline-variant">·</span>
            <Link to="/register/supplier" className="hover:text-primary">مورّد</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

function SectionHead({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="flex flex-col gap-space-xs">
      <span className="font-small-medium text-small-medium text-tertiary">{eyebrow}</span>
      <h2 className="font-display text-[26px] font-semibold tracking-tight text-on-surface md:text-[32px]">{title}</h2>
    </div>
  )
}

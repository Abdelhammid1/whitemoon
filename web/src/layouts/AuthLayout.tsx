import type { ReactNode } from 'react'
import logoUrl from '../assets/white-moon-logo.png'

/** Branded split layout: a midnight-navy hero panel beside a white form card.
 *  Stacks to one column on mobile. Shared by login / register / OTP / 2FA. */
export function AuthLayout({
  title,
  subtitle,
  children,
  footerLinks,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  footerLinks?: ReactNode
}) {
  return (
    <main className="w-full min-h-screen grid grid-cols-1 md:grid-cols-2 bg-surface">
      {/* Brand hero (right in RTL) */}
      <aside className="relative overflow-hidden bg-primary text-on-primary px-space-xl py-space-xl flex flex-col justify-between min-h-[200px] md:min-h-screen">
        <div
          aria-hidden
          className="absolute -top-24 -left-24 w-[420px] h-[420px] rounded-full opacity-20"
          style={{ background: 'radial-gradient(circle, #a8812b 0%, transparent 70%)' }}
        />
        <div className="relative flex items-center gap-space-sm">
          <img src={logoUrl} alt="White Moon" width={44} height={44} style={{ width: 44, height: 44, objectFit: 'contain' }} />
          <div className="flex flex-col leading-tight">
            <span className="font-headline-2 text-headline-2 font-medium">وايت مون</span>
            <span className="font-mono-body text-[11px] text-primary-fixed-dim tracking-widest">WHITE MOON</span>
          </div>
        </div>
        <div className="relative hidden md:flex flex-col gap-space-sm max-w-[360px]">
          <h2 className="font-display text-display font-medium tracking-tight">
            منصّة الأعمال والتجارة بالجملة
          </h2>
          <p className="font-body text-body text-primary-fixed-dim">
            موردون وعملاء في مكان واحد — طلبات، ائتمان آجل، مستودعات، ولوجستيات، بإدارة محاسبية كاملة.
          </p>
        </div>
        <div className="relative font-mono-body text-[11px] text-primary-fixed-dim tracking-tight">
          جميع المعاملات بالجنيه المصري (EGP) · بنية مؤسسية آمنة
        </div>
      </aside>

      {/* Form side (left in RTL) */}
      <section className="flex items-center justify-center px-space-lg py-space-xl">
        <div className="w-full max-w-[380px] flex flex-col">
          <div className="mb-space-xl">
            <h1 className="font-headline-1 text-headline-1 text-on-surface font-medium mb-1">{title}</h1>
            {subtitle && <p className="font-small text-small text-secondary">{subtitle}</p>}
          </div>
          <div className="w-full flex flex-col">{children}</div>
          {footerLinks && (
            <div className="w-full flex items-center justify-center gap-3 font-small text-small text-secondary mt-space-xl">
              {footerLinks}
            </div>
          )}
        </div>
      </section>
    </main>
  )
}

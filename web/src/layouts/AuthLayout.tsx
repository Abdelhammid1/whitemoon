import type { ReactNode } from 'react'
import { Brand } from '../components/Brand'

/** Centered 360px column from the Stitch export (login/register/OTP/2FA). */
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
    <main className="w-full min-h-screen flex items-start justify-center p-space-lg bg-surface-container-lowest">
      <div className="w-full max-w-[360px] pt-[120px] flex flex-col items-center">
        <div className="flex flex-col items-center mb-8">
          <Brand size={36} />
        </div>
        <div className="w-full text-center mb-8">
          <h1 className="font-headline-1 text-headline-1 text-on-surface mb-2">{title}</h1>
          {subtitle && <p className="font-small text-small text-secondary">{subtitle}</p>}
        </div>
        <div className="w-full flex flex-col">{children}</div>
        {footerLinks && (
          <div className="w-full flex items-center justify-center gap-3 font-small text-small text-secondary mt-8">
            {footerLinks}
          </div>
        )}
        <div className="w-full text-center mt-8">
          <span className="font-mono-body text-[11px] text-outline tracking-tight">
            جميع المعاملات بالجنيه المصري (EGP) · بنية مؤسسية آمنة
          </span>
        </div>
      </div>
    </main>
  )
}

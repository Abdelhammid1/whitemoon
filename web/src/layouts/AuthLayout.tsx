import type { ReactNode } from 'react'

/**
 * Centered page for unauthenticated flows (login / register / OTP / 2FA).
 * Follows DESIGN.md: parchment background, centered column, no shadows
 * outside the card itself.
 */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-parchment text-ink">
      <div className="mx-auto flex min-h-screen max-w-[640px] flex-col items-center justify-center px-6 py-10">
        <div className="mb-8 flex items-center gap-2">
          <div className="h-4 w-4 rounded-sm bg-ink" aria-hidden />
          <span className="text-body-lg text-ink">وايت مون</span>
        </div>
        <div className="w-full">{children}</div>
      </div>
    </div>
  )
}

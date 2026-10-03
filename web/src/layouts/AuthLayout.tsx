import type { ReactNode } from 'react'
import { Brand } from '../components/Brand'

/**
 * Centered page for unauthenticated flows. DESIGN.md stays strict:
 * parchment canvas, 400–500 weights, hairline borders, teal reserved.
 * Composition only — brand gets room, the card has serious internal
 * padding, and a column max-width of 420px keeps the surface compact
 * on huge screens instead of looking lost at 640px.
 */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-parchment text-ink">
      <div className="mx-auto flex min-h-screen w-full max-w-[420px] flex-col items-stretch justify-center px-6 py-12">
        <div className="mb-10 flex items-center justify-center">
          <Brand size={36} />
        </div>
        {children}
        <p className="mt-8 text-center text-caption text-ash">
          © {new Date().getFullYear()} وايت مون · منصة الأعمال
        </p>
      </div>
    </div>
  )
}

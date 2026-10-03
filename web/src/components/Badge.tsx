import type { ReactNode } from 'react'

type Tone = 'teal' | 'neutral' | 'muted'

interface Props {
  tone?: Tone
  children: ReactNode
}

/**
 * Badge from DESIGN.md: 9999px pill, weight 500 at 11px, 2/8 padding.
 * `teal` is the "NEW" style; neutral/muted use graphite borders only.
 * Teal reserved per DESIGN rules — use `neutral` for status chips.
 */
export function Badge({ tone = 'neutral', children }: Props) {
  const toneClass: Record<Tone, string> = {
    teal: 'bg-deep-teal text-parchment',
    neutral: 'bg-parchment text-ink border border-warm-mist',
    muted: 'bg-parchment text-graphite border border-warm-mist',
  }
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-caption font-medium ${toneClass[tone]}`}
    >
      {children}
    </span>
  )
}

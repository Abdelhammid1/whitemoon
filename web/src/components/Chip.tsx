import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean
  children: ReactNode
}

/**
 * Pill chip from DESIGN.md: 9999px radius, 8/12 padding, 14px weight 400.
 * Active fills with Deep Teal and white text.
 */
export function Chip({ active = false, className = '', children, ...rest }: Props) {
  const base =
    'inline-flex items-center rounded-full px-3 py-2 text-body transition-colors min-h-8'
  const stateClass = active
    ? 'bg-deep-teal text-parchment'
    : 'bg-transparent text-ink border border-warm-mist hover:border-ink'
  return (
    <button type="button" className={`${base} ${stateClass} ${className}`} {...rest}>
      {children}
    </button>
  )
}

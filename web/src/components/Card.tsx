import type { HTMLAttributes, ReactNode } from 'react'

interface Props extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  /** When true, uses the "suggestion card" surface + hairline shadow. */
  elevated?: boolean
}

export function Card({ children, elevated = false, className = '', ...rest }: Props) {
  const base = 'rounded-2xl p-4'
  const bg = elevated ? 'bg-soft-paper card-shadow' : 'bg-parchment border border-warm-mist'
  return (
    <div className={`${base} ${bg} ${className}`} {...rest}>
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3 flex flex-col gap-1">
      <h2 className="text-body-lg text-ink">{title}</h2>
      {subtitle && <p className="text-body-sm text-graphite">{subtitle}</p>}
    </div>
  )
}

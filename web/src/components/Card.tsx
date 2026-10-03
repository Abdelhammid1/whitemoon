import type { HTMLAttributes, ReactNode } from 'react'

type Pad = 'md' | 'lg' | 'xl'

interface Props extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  /** When true, uses the "suggestion card" surface + hairline shadow. */
  elevated?: boolean
  /** DESIGN.md pins card padding at 16px; `lg`/`xl` give hero/login more room. */
  padding?: Pad
}

const PADDING_CLASS: Record<Pad, string> = {
  md: 'p-4',
  lg: 'p-6',
  xl: 'p-8',
}

export function Card({
  children,
  elevated = false,
  padding = 'md',
  className = '',
  ...rest
}: Props) {
  const base = `rounded-2xl ${PADDING_CLASS[padding]}`
  const bg = elevated
    ? 'bg-soft-paper card-shadow'
    : 'bg-soft-paper border border-warm-mist'
  return (
    <div className={`${base} ${bg} ${className}`} {...rest}>
      {children}
    </div>
  )
}

export function CardHeader({
  title,
  subtitle,
}: {
  title: string
  subtitle?: string
}) {
  return (
    <div className="mb-5 flex flex-col gap-1">
      <h2 className="text-body-lg text-ink" style={{ fontWeight: 500 }}>
        {title}
      </h2>
      {subtitle && <p className="text-body text-graphite">{subtitle}</p>}
    </div>
  )
}

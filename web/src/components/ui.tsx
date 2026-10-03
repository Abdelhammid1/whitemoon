import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'
import { forwardRef } from 'react'
import { Icon } from './Icon'

/* ---------------------------------------------------------------- Button */

type ButtonVariant = 'primary' | 'secondary' | 'destructive'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  iconRight?: string
  children: ReactNode
}

export function Button({
  variant = 'secondary',
  iconRight,
  className = '',
  type = 'button',
  children,
  ...rest
}: ButtonProps) {
  const base =
    'inline-flex items-center justify-center gap-space-sm rounded-lg py-2 px-4 transition-all active:scale-[0.99] disabled:opacity-40 disabled:cursor-not-allowed'
  const variants: Record<ButtonVariant, string> = {
    primary:
      'bg-primary text-on-primary font-body-medium text-body-medium hover:bg-neutral-800',
    secondary:
      'bg-surface-container-lowest border border-surface-container-high text-primary font-body-medium text-body-medium hover:bg-surface',
    destructive:
      'bg-surface-container-lowest border border-surface-container-high text-[#B3261E] font-body-medium text-body-medium hover:bg-surface',
  }
  return (
    <button type={type} className={`${base} ${variants[variant]} ${className}`} {...rest}>
      {children}
      {iconRight && <Icon name={iconRight} size={18} />}
    </button>
  )
}

/* ---------------------------------------------------------------- Pill */

type PillTone = 'signal' | 'warning' | 'error' | 'neutral'

const PILL_TONE: Record<PillTone, string> = {
  signal: 'bg-[#0F6B3E]/10 text-[#0F6B3E]',
  warning: 'bg-[#A8650C]/10 text-[#A8650C]',
  error: 'bg-[#B3261E]/10 text-[#B3261E]',
  neutral: 'bg-surface-variant text-on-surface-variant',
}

export function Pill({ tone = 'neutral', children }: { tone?: PillTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full font-mono-body text-small ${PILL_TONE[tone]}`}
    >
      {children}
    </span>
  )
}

/* ---------------------------------------------------------------- Dot */

export function Dot({ tone = 'neutral' }: { tone?: PillTone }) {
  const color: Record<PillTone, string> = {
    signal: 'bg-[#0F6B3E]',
    warning: 'bg-[#A8650C]',
    error: 'bg-[#B3261E]',
    neutral: 'bg-secondary',
  }
  return <span className={`inline-block shrink-0 w-2 h-2 rounded-full ${color[tone]}`} />
}

/* ---------------------------------------------------------------- Field (underline input) */

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  hint?: ReactNode
  error?: string | null
  mono?: boolean
}

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, hint, error, mono = false, className = '', id, ...rest },
  ref,
) {
  const inputId = id ?? rest.name
  const fontClass = mono ? 'font-mono-body text-mono-body' : 'font-body text-body'
  const borderClass = error
    ? 'border-[#B3261E] focus:border-[#B3261E]'
    : 'border-surface-container-high focus:border-primary'
  return (
    <div className="w-full flex flex-col">
      {label && (
        <label htmlFor={inputId} className="font-small text-small text-secondary mb-1">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={`w-full bg-transparent ${fontClass} text-on-surface py-2 border-b ${borderClass} focus:border-b-2 focus:outline-none transition-all placeholder:text-outline-variant ${className}`}
        {...rest}
      />
      {error ? (
        <span className="mt-1 font-small text-small text-[#B3261E]">{error}</span>
      ) : hint ? (
        <span className="mt-1 font-small text-small text-outline">{hint}</span>
      ) : null}
    </div>
  )
})

/* ---------------------------------------------------------------- Page scaffolding */

export function PageTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="flex flex-col">
      <h1 className="font-display text-display text-primary font-medium tracking-tight">{title}</h1>
      {subtitle && <p className="font-body text-body text-secondary mt-space-xs">{subtitle}</p>}
    </header>
  )
}

export function SectionHeader({
  title,
  action,
}: {
  title: string
  action?: ReactNode
}) {
  return (
    <div className="flex items-baseline justify-between pb-space-sm border-b border-surface-container-highest">
      <h2 className="font-headline-1 text-headline-1 text-primary font-medium">{title}</h2>
      {action}
    </div>
  )
}

/* ---------------------------------------------------------------- states */

export function Spinner({ label = 'جار التحميل…' }: { label?: string }) {
  return <div className="py-space-xl text-center font-body text-body text-secondary">{label}</div>
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="py-[64px] flex flex-col items-center text-center">
      <p className="font-body-medium text-body-medium text-on-surface">{title}</p>
      {description && (
        <p className="mt-space-xs font-body text-body text-secondary max-w-[420px]">
          {description}
        </p>
      )}
      {action && <div className="mt-space-md">{action}</div>}
    </div>
  )
}

export function InlineError({ message }: { message: string }) {
  return (
    <div className="font-small text-small text-[#B3261E] border-b border-[#B3261E]/30 pb-space-xs">
      {message}
    </div>
  )
}
